# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python CLI tool that scrapes idol artist live event schedules from official websites and syncs them to a Notion database, with Discord notifications. Uses Claude/Gemini API to automatically analyze unfamiliar website structures from just a `base_url`.

**Status:** Design complete, implementation in progress. `src/` is currently empty; `docs/` contains the full specification.

## Setup

依存関係は `pyproject.toml` で管理（Python 3.10+、uv 必須）。

```bash
uv sync
cp .env.example .env  # then fill in secrets
```

Required env vars in `.env`:
- `NOTION_TOKEN`, `NOTION_DATABASE_ID`
- `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`
- `DISCORD_WEBHOOK_URL` (optional)
- `AI_PROVIDER=auto` (auto|claude|gemini)

## CLI Commands (to be implemented in `src/main.py`)

```bash
uv run python src/main.py analyze [--artist NAME] [--force]   # Phase 1: AI analyzes site, writes YAML config
uv run python src/main.py scrape  [--artist NAME] [--dry-run]  # Phase 2: scrape events → Notion + Discord
uv run python src/main.py enrich  [--artist NAME]              # Phase 3: AI fills missing fields
```

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

## Module Layout (target)

```
src/
├── main.py            # CLI entry point (analyze/scrape/enrich subcommands)
├── config.py          # load_config(), ArtistConfig, AppConfig
├── models/event.py    # LiveEvent dataclass — dedup key: (artist, title, date)
├── ai/provider.py     # AIProvider ABC + ClaudeProvider + GeminiProvider
├── analyzer/          # site_analyzer.py (capture + AI call), config_writer.py
├── scrapers/          # base.py, url_generator.py, generic.py
├── notion/client.py   # fetch_all, create, update, upsert_events
├── notifier/discord.py
└── enricher/enricher.py
```

## Design Documents

実装前に必ず対応ドキュメントを読むこと:

- `docs/requirements.md` — 機能要件 FR-01〜FR-06
- `docs/basic-design.md` — モジュールインターフェース・YAML スキーマ・エラーハンドリング方針
- `docs/architecture.md` — 両フェーズの Mermaid フロー図
- `docs/implementation-plan.md` — 3 マイルストーン × 16 Pod → 7 タスク構成
- `docs/tasks/task-N/unit_*.md` — ユニットごとのインターフェース仕様と完了基準

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
