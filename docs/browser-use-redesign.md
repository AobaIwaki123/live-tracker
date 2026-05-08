# browser-use によるバックエンド全面リプレイス設計

## 背景と動機

現行の 2 フェーズ設計（Analyze → Scrape）の課題:

1. **YAML メンテナンスコスト** — サイトが更新されるたびに CSS セレクタ・ナビゲーション設定を手動修正する必要がある
2. **Analyze フェーズの脆弱性** — AI 解析が失敗した際のデバッグが複雑で、再解析には `--force` が必要
3. **設定爆発** — アーティスト 1 件あたり 30〜50 行の YAML（selector, body_template, mapping 等）が必要
4. **抽象化の重み** — NavigationType × 5 種類、URLGenerator、GenericScraper など、実際の多様なサイト構造を無理に型にはめている

browser-use による自律エージェントに置き換えることで、これらをすべて解消できる。

---

## 新アーキテクチャ概要

```
config/artists.yaml (name + base_url のみ)
         ↓
ScraperAgent (browser-use)
  - LLM がブラウザを自律操作してスケジュールページを発見・取得
  - ページネーション・詳細ページも自動で追跡
  - 構造化 JSON として LiveEvent リストを返却
         ↓
LiveEvent オブジェクト
         ↓
LocalStore (SQLite) → NotionClient → DiscordNotifier
```

**消えるもの**: Analyze フェーズ、NavigationType 分類、URLGenerator、GenericScraper、ConfigWriter  
**変わらないもの**: SQLite、Notion、Discord、FastAPI、モデル層、k8s 構成

---

## 新 YAML スキーマ（最小化）

```yaml
artists:
  - name: avam
    display_name: "AVAM"
    base_url: https://avam-fc.com/schedule
    theme_color: "#FF6B9D"
    image_url: https://example.com/avam.jpg
    scrape_months: 3          # 何ヶ月先まで取得するか（省略時 3）
```

`analyzed_at` / `fetch` / `navigation` / `response` / `selectors` / `detail` は不要になる。

---

## 新モジュール構成

### 削除するモジュール

| モジュール | 理由 |
|-----------|------|
| `src/analyzer/` (site_analyzer.py, config_writer.py) | Analyze フェーズごと廃止 |
| `src/scrapers/` (base.py, generic.py, url_generator.py) | browser-use に置き換え |
| `src/ai/provider.py` | browser-use が langchain 経由でモデルを直接利用する |
| `src/enricher/enricher.py` | スクレイプのタスク指示に統合（opt-in は維持） |

### 新規追加

```
src/agent/
├── __init__.py
└── scraper_agent.py    # browser-use Agent ラッパー
```

### 変更するモジュール

| モジュール | 変更内容 |
|-----------|---------|
| `src/config.py` | ArtistConfig を最小化（base_url + display_name + theme_color + scrape_months） |
| `src/main.py` | `analyze` サブコマンドを削除、`scrape` を ScraperAgent 呼び出しに変更 |

### 変更しないモジュール

- `src/models/event.py`
- `src/store/local_store.py`
- `src/notion/client.py`
- `src/notifier/discord.py`
- `src/notifier/weekly_summary.py`
- `src/web/app.py`（WebSocket の進捗通知は ScraperAgent に合わせて調整）

---

## ScraperAgent 設計

### インターフェース

```python
# src/agent/scraper_agent.py
async def scrape_artist(
    artist: ArtistConfig,
    dry_run: bool = False,
) -> list[LiveEvent]:
    """browser-use Agent でアーティストのライブスケジュールを取得する。"""
```

### Agent タスク指示（プロンプト）

```python
task = f"""
あなたはアイドルのライブスケジュール収集エージェントです。

以下の URL から、アーティスト「{artist.display_name}」の
今日から {artist.scrape_months} ヶ月先までのライブイベントを収集してください。

URL: {artist.base_url}

手順:
1. ページを開き、ライブスケジュールが表示されているか確認する
2. スケジュールが見当たらない場合は、ナビゲーションから schedule / live / event などのリンクを探して遷移する
3. 月ごとのページネーションがある場合は {artist.scrape_months} ヶ月分を順番に取得する
4. 各イベントについて detail ページのリンクがあれば開いて venue と ticket_url を補完する

取得するフィールド (取得できない場合は null):
- title: イベント名（必須）
- date: 日付 (YYYY-MM-DD 形式、必須)
- start_time: 開演時刻 (HH:MM 形式)
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
import json

async def scrape_artist(artist: ArtistConfig, dry_run: bool = False) -> list[LiveEvent]:
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001")  # コスト最適化
    agent = Agent(task=_build_task(artist), llm=llm)
    
    result = await agent.run()
    raw = json.loads(result.final_result())
    
    return [_to_live_event(item, artist.name) for item in raw]
```

---

## 新 CLI コマンド

```bash
uv run python src/main.py scrape [--artist NAME] [--dry-run]   # 自律スクレイプ
uv run python src/main.py summary                               # Discord 週次サマリー
```

`analyze` コマンドは廃止。

---

## 依存パッケージの変更

### 追加

```toml
browser-use          # 自律ブラウザエージェント
langchain-anthropic  # browser-use の LLM バックエンド
langchain-google-genai  # Gemini バックエンド（fallback）
```

### 削除

```toml
scrapling[all]   # GenericScraper が不要になるため削除
```

### 維持

```toml
playwright       # browser-use が内部で使用
anthropic        # Notion client などで直接使う場合は維持（要確認）
google-genai     # langchain-google-genai に置き換えか要確認
```

---

## コスト試算

| 構成 | 1 アーティストあたりの推定 LLM コール数 | 備考 |
|------|----------------------------------------|------|
| 現行（Analyze 済み後の scrape） | 0 | YAML ドリブン、AI 不使用 |
| browser-use / claude-haiku-4-5 | 5〜20 ステップ | ページ数・pagination 次第 |
| browser-use / claude-sonnet-4-6 | 5〜20 ステップ | haiku より高精度、高コスト |

13 アーティスト × 日次実行では haiku モデルが現実的。  
精度に問題が出た場合のみ sonnet にグレードアップする。

---

## 信頼性とフォールバック

browser-use は LLM 依存なため以下のリスクがある:

| リスク | 対策 |
|--------|------|
| 結果が空（ページ構造を誤認） | リトライ回数上限（max_steps）設定、ログ記録 |
| JSON 形式が崩れる | Pydantic バリデーション + partial save |
| レート制限 | アーティストを順次実行（並列しない）、sleep 追加 |
| サイトが bot 検知 | browser-use はリアルブラウザを使うため既存の scrapling より検知されにくい |

---

## 廃止される docs

リプレイス完了後に削除するドキュメント:

| ファイル | 理由 |
|----------|------|
| `docs/requirements.md` | 要件が変わるため書き直し |
| `docs/basic-design.md` | モジュール構成が変わるため書き直し |
| `docs/architecture.md` | フロー図が変わるため書き直し |
| `docs/analyze-loop-design.md` | Analyze フェーズごと廃止 |
| `docs/scraping-investigation-tips.md` | CSS セレクタデバッグが不要になる |
| `docs/artist-update-workflow.md` | YAML が最小化されるため簡略版に書き直し |

維持するドキュメント: `docs/discord-summary-format.md`, `docs/frontend-design.md`

---

## 移行ステップ

1. **PoC** — `browser-use` を 1〜2 アーティストで試し、JSON 出力の品質・コストを確認
2. **ScraperAgent 実装** — `src/agent/scraper_agent.py` + 新 `config.py` + 新 `main.py`
3. **旧モジュール削除** — `src/analyzer/`, `src/scrapers/`, `src/ai/`, `src/enricher/`
4. **artists.yaml 簡略化** — 既存 13 アーティストの設定を name + base_url + theme_color のみに削ぎ落とす
5. **docs 更新** — 上記廃止リストを削除し、新設計に合わせた requirements / basic-design / architecture を書き直す
6. **k8s 更新** — scraper CronJob のコマンドは `scrape` のままで変更不要
