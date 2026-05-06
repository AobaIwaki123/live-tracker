# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python CLI tool that scrapes idol artist live event schedules from official websites and syncs them to a Notion database, with Discord notifications. Uses Claude/Gemini API to automatically analyze unfamiliar website structures from just a `base_url`.

**Status:** 全モジュール実装済み。`docs/` に仕様書、`src/` に実装、`config/artists.yaml` に設定ファイル。

## Setup

依存関係は `pyproject.toml` で管理（Python 3.10+、uv 必須）。

```bash
uv sync
cp .env.example .env  # then fill in secrets
```

## 依存パッケージの管理

### 脆弱性チェック（必須）

依存パッケージを追加・更新するときは **必ず** 以下を実行し、既知の脆弱性がないことを確認すること。

```bash
uv run pip-audit        # 脆弱性チェック
uv pip list --outdated  # アップデート確認
```

脆弱性が検出された場合は修正してから変更をコミットする。

### アップデート方針

- 直接依存は `uv add <package>==<latest>` または `uv lock --upgrade-package <package>` で更新する。
- `scrapling[all]` の推移的依存（playwright / patchright）は scrapling 側が exact pin しているため、scrapling 本体のアップデートを待つ。

Required env vars in `.env`:
- `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` (少なくとも一方が必須)
- `NOTION_TOKEN`, `NOTION_DATABASE_ID` (Notion 連携を使う場合のみ)
- `DISCORD_WEBHOOK_URL` (optional)
- `AI_PROVIDER=auto` (auto|claude|gemini)

## CLI Commands

```bash
uv run python src/main.py analyze [--artist NAME] [--force]   # Phase 1: AI analyzes site, writes YAML config
uv run python src/main.py scrape  [--artist NAME] [--dry-run]  # Phase 2: scrape events → SQLite + Notion + Discord
uv run python src/main.py enrich  [--artist NAME]              # Phase 3: AI fills missing fields
uv run python src/main.py summary                              # 直近 14 日のサマリーを Discord に送信
```

## Docker Build & Deploy

**バージョニング**: `git rev-parse --short HEAD`（コミット SHA）をイメージタグとして使う。`make release` が自動で処理する。

```bash
make release   # build → push → manifest 更新 → git commit → push
make status    # pod / cronjob / pvc の状態確認
make logs      # backend ログ
make scrape    # scraper を今すぐ手動実行
```

## k8s デプロイ手順（初回のみ）

```bash
# 1. Secret を手動で作成（Git には入れない）
cp k8s/manifests/secret.yaml.example k8s/manifests/secret.yaml
# secret.yaml の値を埋める
kubectl apply -f k8s/manifests/secret.yaml

# 2. 全 manifest を適用
make apply

# 3. ArgoCD Application を登録
kubectl apply -f k8s/argocd/app.yml

# 以降のデプロイは make release だけ
```

**構成**:
- `frontend` (nginx): HTML 配信 + `/api`, `/img` を backend にプロキシ
- `backend` (FastAPI): API サーバー、ポート 8000
- `scraper` (CronJob): 毎日 0:00 UTC (9:00 JST) に `scrape` を実行
- `summary` (CronJob): 毎週月曜 0:00 UTC (9:00 JST) に Discord サマリー送信
- `live-tracker-data` (PVC): SQLite `data/events.db` を永続化

## Architecture

### 2-Phase Design: Analyze → Scrape

**WHY** サイト解析（高コスト・一度きり）とスクレイピング（低コスト・定期実行）を分離する。  
**WHY NOT** 毎回スクレイピング時に AI 解析しない — API コストが定期実行のたびに発生し、レート制限にも当たる。

#### Phase 1 — Analyze（一度きり）
1. `DynamicFetcher` が `base_url` をロードし、HTML + XHR/Fetch ネットワークログをキャプチャ
2. AI が Navigation タイプ・セレクタ・API 仕様を判定
3. `ConfigWriter` が結果を `config/artists.yaml` へ書き戻し、`analyzed_at` を記録

#### Phase 2 — Scrape（定期実行）
1. `URLGenerator` が YAML 設定から N ヶ月分の URL / API リクエストを生成
2. `GenericScraper` が HTML 取得または API 呼び出し
3. CSS セレクタ（HTML 型）または JSON マッピング（API 型）で `LiveEvent` を抽出
4. `NotionClient` が差分検出してアップサート（新規作成 or 差分フィールドのみ上書き）
5. Discord Webhook で新規・更新イベントを通知

---

### Navigation タイプの設計

**WHY** アーティストサイトのスケジュール表示方式が 5 種類に分類できる。この分類を YAML に持たせることで、コードを変えずにサイトを追加できる。  
**WHY NOT** サイトごとにスクレイパークラスを書かない — アーティストが増えるたびにコード変更が必要になる。

| Type | Mechanism |
|------|-----------|
| `single_page` | 全件が 1 URL に掲載 |
| `query_param` | `?d=2026-05-01` でページ切り替え |
| `path_segment` | `/schedule/2026/05` の URL 構造 |
| `pagination_links` | 次ページリンクを辿る |
| `api_endpoint` | JS が内部 API を叩く（avam-fc.com 型） |

AI への解析プロンプトでは `api_endpoint` を最優先で判定する指示を入れる。内部 API の方が HTML より構造が安定しているため。

---

### Notion をスクレイプデータで上書きする

**WHY** スクレイプデータを正として扱い、Notion の手動編集も含めて差分があるフィールドを上書きする。これによりデータの一貫性を保証できる。  
**WHY NOT** 手動入力を保護しない — 保護ロジックを入れると「どちらが正しいか」の競合管理が必要になり、個人ツールとして複雑すぎる。

---

### `enrich` コマンドを opt-in にする

**WHY** チケットサイト（e+・チケットぴあ・ローチケ）へのアクセスはレート制限・構造変化リスクがある。また scrape とは独立した高コスト処理なので、明示的に実行する設計にする。  
**WHY NOT** `scrape` に自動組み込みしない — 定期実行の `scrape` が外部チケットサイトに毎回アクセスすると、IP ブロックや意図しないリクエスト増加が起きる。

---

### AI Provider を抽象化する

**WHY** Claude API と Gemini API のどちらか一方が使えれば動作するようにする。個人開発のため API キーのコスト・可用性が変わりうる。  
**WHY NOT** Claude に固定しない — ベンダーロックインを避け、コスト最適化の選択肢を残す。

`AIProvider` ABC に `complete(system, user) -> str` の 1 メソッドのみ定義し、`get_ai_provider()` が `AI_PROVIDER` 環境変数に応じてインスタンスを返す。

---

### Discord を Webhook で通知する

**WHY** ステートレスな HTTP POST だけで完結し、Bot のポーリングプロセスを常駐させる必要がない。個人ツールとして運用コストが最小。  
**WHY NOT** Discord Bot を使わない — Bot はサーバー参加・権限設定・常駐プロセスが必要で、cron 実行の scrape コマンドとの相性が悪い。

---

### Tiered データ取得戦略

**WHY** 公式サイトによっては会場・チケット URL が「coming soon」のまま公演直前まで未確定なことがある。欠損を失敗扱いにせず、取得できたフィールドだけで Notion 登録する。

```
Tier 1: 公式サイト メインページ → title / date（必須）
Tier 2: 公式サイト 詳細ページ  → venue / start_time / other_artists
Tier 3: AI エンリッチメント    → ticket_price / prefecture（enrich コマンドで opt-in）
```

`fetch_status` フィールドが現在の取得レベルを記録し、enrich の対象絞り込みに使う。

---

## Module Layout

```
src/
├── main.py            # CLI entry point (analyze/scrape/enrich/summary subcommands)
├── config.py          # load_config(), ArtistConfig, AppConfig
├── models/event.py    # LiveEvent dataclass — dedup key: (artist, title, date)
├── ai/provider.py     # AIProvider ABC + ClaudeProvider + GeminiProvider
├── analyzer/          # site_analyzer.py (capture + AI call), config_writer.py
├── scrapers/          # base.py, url_generator.py, generic.py
├── notion/client.py   # fetch_all, create, update, upsert_events
├── notifier/
│   ├── discord.py         # Discord Webhook 通知（新規・更新イベント）
│   └── weekly_summary.py  # Discord 週次サマリー送信
├── store/
│   └── local_store.py     # ローカル SQLite イベントキャッシュ
└── enricher/enricher.py
```

## Design Documents

実装前に必ず対応ドキュメントを読むこと:

- `docs/requirements.md` — 機能要件 FR-01〜FR-06
- `docs/basic-design.md` — モジュールインターフェース・YAML スキーマ・エラーハンドリング方針
- `docs/architecture.md` — 両フェーズの Mermaid フロー図
- `docs/implementation-plan.md` — 3 マイルストーン × 16 Pod → 7 タスク構成
- `docs/tasks/task-N/unit_*.md` — ユニットごとのインターフェース仕様と完了基準

## Docstring & 型ヒント規約

`src/` 配下のすべてのファイルに適用する。

### スタイル: Google 形式

```python
def func(self, arg: Type) -> ReturnType:
    """概要。

    Args:
        arg: 説明。

    Returns:
        説明。

    Raises:
        ExceptionType: 発生条件。
    """
```

### 実装時のルール

1. **型ヒント必須** — 全関数のシグネチャに付ける。docstring 内に型を重複させない。
2. **モジュールレベル docstring** — 各ファイルの先頭に役割と参照先を書く。
   ```python
   """モジュールの役割。(参照: docs/xxx.md § YYY)"""
   ```
3. **docstring の内容は `docs/` から転写** — 実装対象モジュールの対応ドキュメントを参照:
   - `src/models/event.py` → `docs/basic-design.md` § データモデル
   - `src/config.py` → `docs/basic-design.md` § ArtistConfig
   - `src/notion/client.py` → `docs/basic-design.md` § NotionClient, `docs/requirements.md` § FR-03
   - `src/ai/provider.py` → `docs/basic-design.md` § AIProvider
   - `src/analyzer/` → `docs/basic-design.md` § SiteAnalyzer, `docs/tasks/task-6/`
   - `src/scrapers/` → `docs/basic-design.md` § URLGenerator / GenericScraper, `docs/tasks/task-3/`
   - `src/notifier/discord.py` → `docs/requirements.md` § FR-04
   - `src/notifier/weekly_summary.py` → `docs/tasks/task-8/unit_2.md`
   - `src/store/local_store.py` → `docs/tasks/task-8/unit_1.md`
   - `src/enricher/enricher.py` → `docs/requirements.md` § FR-06
4. **`_` プレフィックスの関数・クラスは docstring 不要** — pdoc の出力から除外される。

### API ドキュメントのビルド

```bash
uv run pdoc src/ --output-dir docs/api --template-directory ./templates   # → docs/api/ に HTML を生成
```

---

## Configuration Schema (`config/artists.yaml`)

ユーザーが書くのは `name` + `base_url` のみ。`analyze` が残りを自動生成する:

```yaml
artists:
  - name: avam-fc
    base_url: https://avam-fc.com/schedule
    analyzed_at: "2026-05-04"      # --force なしは再解析しない
    fetch:
      dynamic: true                # Playwright 必要
    navigation:
      type: api_endpoint
      endpoint: /api/schedule/get
      method: POST
      body_template: {start: "{month_start}", end: "{month_end}"}
      range_months: 3
    response:
      format: json_array
      mapping: {title: title, date: reception_date, date_format: "%Y-%m-%d"}
    detail:
      enabled: true
      url_pattern: "{base_url}/detail/{id}?d={date}"
      selectors:
        venue: ".venue-name"
        ticket_url: "a.ticket::attr(href)"
```
