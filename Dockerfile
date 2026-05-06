FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# Install Chromium + system deps via Playwright
RUN uv run playwright install chromium --with-deps

COPY src/ ./src/
COPY config/ ./config/
COPY templates/ ./templates/
COPY frontend/public/img/ ./frontend/public/img/

EXPOSE 8000
CMD ["uv", "run", "python", "src/main.py", "web", "--host", "0.0.0.0", "--port", "8000"]
