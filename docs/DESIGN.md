# Live Tracker — 設計書

## 1. 概要

Python CLI + Web ツール。アイドルアーティストの公式サイトからライブスケジュールを自律的に収集し、SQLite に保存・Notion に同期・Discord に通知する。

**スクレイピング方式**: [browser-use](https://github.com/browser-use/browser-use) による LLM 自律エージェント。サイトごとの CSS セレクタ設定や事前解析フェーズは不要で、`base_url` を渡すだけで動作する。

### 旧設計からの変更点

| | 旧設計 | 新設計 |
|---|---|---|
| フェーズ | Analyze → Scrape の 2 段階 | `scrape` 1 コマンドのみ |
| スクレイピング | YAML 設定 + CSS セレクタ | browser-use Agent が自律判断 |
| YAML | 1 アーティスト 30〜50 行 | `name` + `base_url` + 表示設定のみ |
| 削除モジュール | — | `src/analyzer/`, `src/scrapers/`, `src/ai/`, `src/enricher/` |

---

## 2. アーキテクチャ

```
config/artists.yaml  (name + base_url のみ)
         │
         ▼
src/agent/scraper_agent.py  (browser-use Agent)
  ・LLM がブラウザを自律操作してスケジュールページを発見
  ・ページネーション・詳細ページも自動追跡
  ・構造化 JSON として LiveEvent リストを返却
         │
         ▼
src/models/event.py  (LiveEvent)
         │
    ┌────┴────┐
    ▼         ▼
LocalStore  NotionClient   DiscordNotifier
(SQLite)    (差分 upsert)  (新規・更新を通知)
```

### モジュール一覧

```
src/
├── main.py                # CLI エントリーポイント
├── config.py              # ArtistConfig ロード（最小化済み）
├── models/event.py        # LiveEvent dataclass
├── agent/
│   └── scraper_agent.py   # browser-use Agent ラッパー  ← 新規
├── notion/client.py       # Notion API ラッパー
├── notifier/
│   ├── discord.py         # Discord Webhook 通知
│   └── weekly_summary.py  # Discord 週次サマリー
├── store/local_store.py   # SQLite イベントキャッシュ
└── web/app.py             # FastAPI REST + WebSocket
```

---

## 3. データモデル（LiveEvent）

重複判定キー: `(artist, title, date)`

| フィールド | 型 | 取得元 |
|---|---|---|
| title | str | Agent（必須） |
| artist | str | config |
| date | date \| None | Agent（必須） |
| start_time | str \| None | Agent |
| venue | str \| None | Agent |
| prefecture | str \| None | 会場名から導出 |
| ticket_url | str \| None | Agent |
| other_artists | str \| None | Agent |
| poster_url | str \| None | Agent |
| source_url | str \| None | Agent |
| fetch_status | str | `詳細取得済み` / `タイトル・日付のみ` |

---

## 4. YAML スキーマ（config/artists.yaml）

```yaml
artists:
  - name: avam                           # 識別子（半角英数字）
    display_name: "AVAM"                 # 表示名
    base_url: https://avam-fc.com/schedule
    theme_color: "#FF6B9D"              # UI アクセント色（Hex）
    image_url: https://example.com/avam.jpg
    scrape_months: 3                     # 何ヶ月先まで収集するか（省略時 3）
```

`analyzed_at` / `fetch` / `navigation` / `response` / `selectors` / `detail` はすべて不要。

---

## 5. ScraperAgent（src/agent/scraper_agent.py）

### インターフェース

```python
async def scrape_artist(
    artist: ArtistConfig,
    dry_run: bool = False,
) -> list[LiveEvent]:
    """browser-use Agent でアーティストのライブスケジュールを取得する。"""
```

### Agent タスク指示

```python
task = f"""
あなたはアイドルのライブスケジュール収集エージェントです。

以下の URL から、アーティスト「{artist.display_name}」の
今日から {artist.scrape_months} ヶ月先までのライブイベントを収集してください。

URL: {artist.base_url}

手順:
1. ページを開き、ライブスケジュールが表示されているか確認する
2. 見当たらない場合は schedule / live / event などのリンクを探して遷移する
3. 月ごとのページネーションがある場合は {artist.scrape_months} ヶ月分を順番に取得する
4. 各イベントに detail ページのリンクがあれば開いて venue / ticket_url を補完する

取得するフィールド（取得できない場合は null）:
- title: イベント名（必須）
- date: 日付 YYYY-MM-DD（必須）
- start_time: 開演時刻 HH:MM
- venue: 会場名
- ticket_url: チケット購入 URL
- source_url: イベントの公式ページ URL

結果を JSON 配列として返してください。
"""
```

### 実装スケッチ

```python
from browser_use import Agent
from langchain_anthropic import ChatAnthropic

async def scrape_artist(artist: ArtistConfig, dry_run: bool = False) -> list[LiveEvent]:
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001")  # コスト最適化
    agent = Agent(task=_build_task(artist), llm=llm)

    result = await agent.run()
    raw = json.loads(result.final_result())
    return [_to_live_event(item, artist.name) for item in raw]
```

### コスト試算

| モデル | 1 アーティストあたりの推定ステップ数 | 備考 |
|--------|--------------------------------------|------|
| claude-haiku-4-5 | 5〜20 | 日次 13 アーティストでも現実的 |
| claude-sonnet-4-6 | 5〜20 | 精度不足時のグレードアップ先 |

---

## 6. 周辺モジュール

### LocalStore（src/store/local_store.py）

```
LocalStore
  ├─ upsert(event: LiveEvent) -> None
  ├─ get_upcoming(days: int) -> list[LiveEvent]
  └─ get_all() -> list[LiveEvent]
```

SQLite `data/events.db` に保存。scrape コマンドが常に書き込む。Notion は任意の追加出力先。

### NotionClient（src/notion/client.py）

```
NotionClient
  ├─ fetch_all() -> dict[tuple[str,str,date], NotionRecord]
  ├─ create(event: LiveEvent) -> str
  ├─ update(page_id: str, diff: dict) -> None
  └─ upsert_events(events) -> (新規リスト, 更新リスト)
```

スクレイプデータを正とし、差分フィールドのみ上書きする。

### DiscordNotifier（src/notifier/discord.py）

Webhook POST のみ。Bot 常駐プロセス不要。新規イベント・更新イベントを Embed 形式で通知。URL は `<url>` 形式（ポップアップなし）。

### WeeklySummaryNotifier（src/notifier/weekly_summary.py）

イベントを日付・週でグルーピングし、`docs/discord-summary-format.md` のフォーマットで送信。2000 文字超の場合は週単位で分割。

---

## 7. Web UI / FastAPI（src/web/app.py）

### アーティスト更新ワークフロー

管理画面からアーティスト情報を変更する非同期フロー。

**API エンドポイント:**
- `POST /api/artists/{name}/update` — `display_name`, `theme_color`, `image_url` を受け取り、ジョブ ID を即返却してバックグラウンド処理を開始
- `ws/api/ws/jobs/{job_id}` — WebSocket で進捗をプッシュ通知

**フォームフィールド:**

| フィールド | 説明 |
|-----------|------|
| name | 識別子（半角英数字） |
| display_name | 表示名（任意文字列） |
| theme_color | Hex カラー（カラーピッカー + 直接入力） |
| base_url | スケジュールページ URL |

**処理フロー:**

```
フロントエンド → POST /api/artists/{name}/update
             ← 202 Accepted { job_id }
フロントエンド → WebSocket 接続 (job_id)
             ← [WS] "処理中..." → "完了"
             → artists.yaml を一時ファイル経由で安全に更新（PVC 永続化）
```

---

## 8. CLI コマンド

```bash
uv run python src/main.py scrape [--artist NAME] [--dry-run]   # 自律スクレイプ
uv run python src/main.py summary                               # Discord 週次サマリー
```

`analyze` コマンドは廃止。

---

## 9. 依存パッケージ

### 追加

```toml
browser-use             # 自律ブラウザエージェント
langchain-anthropic     # browser-use の LLM バックエンド
langchain-google-genai  # Gemini バックエンド（fallback）
```

### 削除

```toml
scrapling[all]   # GenericScraper が不要になるため削除
```

### 維持

```toml
playwright       # browser-use が内部で使用
fastapi / uvicorn
python-dotenv / PyYAML / httpx / typer / python-dateutil
```

---

## 10. デプロイ（k8s）

| リソース | 役割 |
|---------|------|
| `backend` Deployment | FastAPI サーバー（ポート 8000） |
| `frontend` Deployment | nginx（HTML 配信 + `/api` プロキシ） |
| `scraper` CronJob | 毎日 0:00 UTC に `scrape` を実行 |
| `summary` CronJob | 毎週月曜 0:00 UTC に Discord サマリー送信 |
| `live-tracker-data` PVC | `data/events.db` と `config/artists.yaml` を永続化 |

`scraper` CronJob のコマンドはリプレイス後も `scrape` のままで変更不要。

---

## 11. エラーハンドリング

| 状況 | 対応 |
|------|------|
| Agent が結果を返さない | リトライ上限（max_steps）後にそのアーティストをスキップしてログ記録 |
| JSON 形式が崩れる | Pydantic バリデーション。パース可能な部分だけ保存 |
| レート制限 | アーティストを順次実行（並列しない）、sleep を挟む |
| Notion API エラー | ログ出力してリトライなしでスキップ |
| 日付パース失敗 | `date=None` として登録 |

---

## 12. 移行計画

1. **PoC** — `browser-use` を 1〜2 アーティストで試し、JSON 出力の品質・コストを確認
2. **ScraperAgent 実装** — `src/agent/scraper_agent.py` + `config.py` 最小化 + `main.py` 差し替え
3. **旧モジュール削除** — `src/analyzer/`, `src/scrapers/`, `src/ai/`, `src/enricher/`
4. **artists.yaml 簡略化** — 既存 13 アーティストの設定を最小スキーマに削ぎ落とす
5. **k8s** — 変更不要（CronJob コマンドは同じ）
