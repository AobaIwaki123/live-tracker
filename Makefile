REGISTRY  := ghcr.io/aobaiwaki123
APP       := live-tracker
GIT_REV   := $(shell git rev-parse --short HEAD)

BACKEND   := $(REGISTRY)/$(APP)-backend:$(GIT_REV)
FRONTEND  := $(REGISTRY)/$(APP)-frontend:$(GIT_REV)
NAMESPACE := live-tracker
MANIFESTS := k8s/manifests

.PHONY: build push release apply status logs scrape exec-scrape summary og help

help: ## Show this help
	@awk 'BEGIN{FS=":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ── Image lifecycle ────────────────────────────────────────────────────────────

build: ## Build backend and frontend images (tag = git SHA)
	docker build --platform linux/amd64 -t $(BACKEND)  .
	docker build --platform linux/amd64 -t $(FRONTEND) ./frontend

push: ## Push images to GHCR
	docker push $(BACKEND)
	docker push $(FRONTEND)

manifest-update: ## Rewrite image tags in k8s manifests to current git SHA
	perl -i -pe 's|(live-tracker-backend:)\S+|$${1}$(GIT_REV)|g'  $(MANIFESTS)/backend.yaml
	perl -i -pe 's|(live-tracker-frontend:)\S+|$${1}$(GIT_REV)|g' $(MANIFESTS)/frontend.yaml

release: ## Full release: build → push → update manifests → git commit → push
	@echo "Releasing $(GIT_REV)..."
	$(MAKE) build push manifest-update
	git add $(MANIFESTS)/backend.yaml $(MANIFESTS)/frontend.yaml
	git commit -m "deploy: $(GIT_REV)"
	git push

# ── k8s ───────────────────────────────────────────────────────────────────────

apply: ## Apply all manifests to k8s (secret は手動で apply)
	kubectl apply -f $(MANIFESTS)/namespace.yaml
	kubectl apply -f $(MANIFESTS)/pvc.yaml
	kubectl apply -f $(MANIFESTS)/backend.yaml
	kubectl apply -f $(MANIFESTS)/frontend.yaml
	kubectl apply -f $(MANIFESTS)/ingress.yaml

status: ## Show pod / cronjob / pvc / ingress status
	kubectl get pods,cronjob,pvc,ingress -n $(NAMESPACE)

logs: ## Stream backend logs
	kubectl logs -f -n $(NAMESPACE) deploy/backend

scrape: ## Trigger scrape via CronJob (new Pod — 本番同等)
	kubectl create job --from=cronjob/scraper scraper-$(shell date +%s) -n $(NAMESPACE)

exec-scrape: ## Trigger scrape directly in running backend pod (即時実行)
	kubectl exec -n $(NAMESPACE) deploy/backend -- uv run python src/main.py scrape

summary: ## Manually trigger a summary job now
	kubectl create job --from=cronjob/summary summary-$(shell date +%s) -n $(NAMESPACE)

# ── Dev ───────────────────────────────────────────────────────────────────────

og: ## Open OG image generator in browser
	open frontend/generate-og.html
