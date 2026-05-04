# 実装計画書 — idol-live-tracker

## 概要

| 項目 | 内容 |
|---|---|
| マイルストーン数 | 3 |
| Pod 総数 | 16 |
| 最終目標 | `base_url` のみ記載すれば AI が構造解析し Notion へ自動転記・Discord 通知・定期実行まで完結 |

---

## Milestone 1 — 手動設定で1サイト動く最小構成

**目標:** YAML にセレクタを手書きすれば Notion に書き込める状態

```
M1-P1 → M1-P2
      → M1-P3 → M1-P4
```

### M1-P1: データモデル・設定基盤

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/models/event.py` / `config/artists.yaml` / `.env` |
| 実装内容 | `LiveEvent` dataclass 定義 / YAML スキーマ確定 / `.env` 読み込み（python-dotenv） |
| 完了条件 | 全 Pod で共通利用できる型定義・設定ロードが揃っている |

**LiveEvent フィールド**

| フィールド | 型 | 取得元 |
|---|---|---|
| title | str | Tier 1: メインページ |
| artist | str | config |
| date | date \| None | Tier 1: メインページ |
| start_time | str | Tier 1〜2 |
| venue | str | Tier 1〜2 |
| prefecture | str | Tier 2〜3（会場から導出） |
| ticket_url | str | Tier 1〜2 |
| ticket_price | str | Tier 3: チケットサイト |
| other_artists | str | Tier 2〜3 |
| source_url | str | config + Tier 1 |
| fetch_status | str | `完全取得` / `一部未取得` / `タイトル・日付のみ` |

重複判定キー: `(artist, title, date)`

---

### M1-P2: Notion Client

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/notion/client.py` |
| 実装内容 | レコード作成（`pages.create`）/ 全レコード取得（`fetch_all`）/ フィールド単位の差分検出（`diff`）/ 差分フィールドのみ更新（`pages.update`） |
| 完了条件 | Notion DB への作成・フィールド単位更新が動作する |
| 依存 | M1-P1 |

**差分検出ロジック**

スクレイプデータを正とし、Notionの手動入力も含め常に上書きする。

```
fetch_all() → dict[(artist, title, date)] → existing_record

for scraped_event in scraped:
    existing = existing_records.get((artist, title, date))

    if existing is None:
        → create（新規）
    else:
        diff = {field: new_val
                for field, new_val in scraped_event
                if existing[field] != new_val and new_val != ""}
        if diff:
            → update(diff)（値が変わったフィールドのみ上書き）
        else:
            → skip（変化なし）
```

**通知トリガー**

| 状態 | Discord 通知 | 内容 |
|---|---|---|
| 新規作成 | ✅ | `🆕 新着ライブ情報` |
| フィールド変更 | ✅ | `🔄 情報が更新されました（更新: 会場名, チケット URL）` |
| 変化なし | — | 通知なし |

**Notion DB プロパティ設計**

| プロパティ名 | 種別 |
|---|---|
| イベントタイトル | タイトル |
| グループ名 | セレクト |
| 開催日 | 日付 |
| 開始時刻 | テキスト |
| 会場名 | テキスト |
| 都道府県 | セレクト |
| チケット URL | URL |
| チケット料金 | テキスト |
| 出演アーティスト | テキスト |
| ポスター画像 URL | URL |
| ソース URL | URL |
| 取得ステータス | セレクト（完全取得 / 一部未取得 / タイトル・日付のみ） |

---

### M1-P3: HTML スクレイパー（single_page）

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/scrapers/base.py` / `src/scrapers/generic.py` |
| 実装内容 | `BaseScraper` 抽象クラス / `GenericScraper` 実装 / `single_page` タイプのみ対応 / CSS セレクタで要素抽出 |
| 完了条件 | `--dry-run` でイベント一覧がターミナルに出力される |
| 依存 | M1-P1 |

---

### M1-P4: CLI 骨格（scrape コマンド）

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/main.py` |
| 実装内容 | `scrape` サブコマンド / アーティストループ / `--artist NAME` オプション / `--dry-run` オプション / 実行サマリ出力 |
| 完了条件 | `python main.py scrape --dry-run` が動作し、Notion 書き込みまで一気通貫で動く |
| 依存 | M1-P2 / M1-P3 |

---

## Milestone 2 — 複数 Navigation タイプ・通知・定期実行

**目標:** 手動設定さえあればどのサイト構造でも動き、Discord 通知と定期実行が使える状態

```
M1完了 → M2-P1 → M2-P2
                → M2-P3 → M2-P4
       → M2-P5（M1-P4 に依存）
       → M2-P6（M2-P5 に依存）
```

### M2-P1: URLGenerator

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/scrapers/url_generator.py` |
| 実装内容 | `navigation.type` に応じた URL / リクエストリスト生成（`single_page` / `query_param` / `path_segment`） |
| 完了条件 | 各タイプで将来 N ヶ月分のターゲットリストが正しく生成される |
| 依存 | M1完了 |

**タイプ別生成ロジック**

| タイプ | 生成内容 |
|---|---|
| `single_page` | `[base_url]` の1件 |
| `query_param` | `base_url?d=2026-05-01`, `?d=2026-06-01` ... を N ヶ月分 |
| `path_segment` | `base_url/2026/05`, `/2026/06` ... を N ヶ月分 |
| `pagination_links` | `base_url` のみ返し Scraper 側で next リンクを追跡 |
| `api_endpoint` | `POST endpoint` × N ヶ月分のボディ |

---

### M2-P2: api_endpoint 対応（avam-fc.com 実機確認）

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/scrapers/generic.py` |
| 実装内容 | `POST` リクエスト送信 / JSON レスポンス → `LiveEvent` マッピング / `response.mapping` 設定の解釈 / 詳細ページ取得（`detail.enabled: true` 時） |
| 完了条件 | avam-fc.com のイベントが Notion DB に転記される（実機確認） |
| 依存 | M2-P1 |
| 備考 | **最もリスクの高い Pod。** API 仕様が非公開のため実機確認を最優先で行う |

---

### M2-P3: DynamicFetcher 統合

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/scrapers/generic.py` |
| 実装内容 | `fetch.dynamic: true` 時に `DynamicFetcher` に切り替え / Playwright セットアップ手順を README に記載 |
| 完了条件 | JS レンダリングが必要なサイトで HTML が取得できる |
| 依存 | M2-P1 |

---

### M2-P4: pagination_links 対応

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/scrapers/generic.py` |
| 実装内容 | `navigation.next_selector` で次ページリンクを取得し再帰的に収集 / `max_pages` で上限制御 |
| 完了条件 | 複数ページにわたるサイトで全件取得できる |
| 依存 | M2-P3 |

---

### M2-P5: Discord Notifier（イベント単位通知）

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/notifier/discord.py` |
| 実装内容 | Webhook への POST（httpx）/ 新規・更新の2種類の Embed 生成 / 更新時は差分フィールド名を列挙 / Webhook URL 未設定時はスキップ / 連続通知間に 0.5 秒の遅延 |
| 完了条件 | 新規追加・フィールド追加の両方で Discord に通知される |
| 依存 | M1-P4 |

**Discord 通知フォーマット（新規）**

```
🆕 新着ライブ情報

🎤 グループ名
📅 2026-08-01  18:00
🏟️ 会場名（都道府県）
🎫 チケット URL

[Notionで見る](https://...)
```

**Discord 通知フォーマット（更新）**

```
🔄 ライブ情報が更新されました

🎤 グループ名  |  イベントタイトル
📅 2026-08-01
✅ 追加された情報: 会場名, チケット URL

[Notionで見る](https://...)
```

---

### M2-P7: LocalStore（SQLite イベントキャッシュ）

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/store/local_store.py` |
| 実装内容 | SQLite テーブル自動作成 / `upsert(event)` — 重複キー `(artist, title, date)` で INSERT OR REPLACE / `get_upcoming(days=14)` / `get_all()` |
| 完了条件 | scrape 後に `data/events.db` へ全イベントが書き込まれる。Notion 設定の有無に関わらず動作する |
| 依存 | M1-P1 |

---

### M2-P8: WeeklySummaryNotifier

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/notifier/weekly_summary.py` / `src/main.py` |
| 実装内容 | `LocalStore.get_upcoming(14)` でイベント取得 / 日付・週単位でグルーピング / `docs/discord-summary-format.md` のフォーマットでメッセージ生成 / 2000 字超は週単位で分割送信 / `python main.py summary` コマンド追加 |
| 完了条件 | `python main.py summary` で直近 2 週間のサマリーが Discord に届く |
| 依存 | M2-P5（Webhook POST の共通処理）/ M2-P7 |

**cron 設定（週次サマリー：毎週月曜 09:00 JST）**

```cron
0 0 * * 1 cd /path/to/idol-live-tracker && uv run python src/main.py summary >> logs/summary-$(date +\%Y-\%m-\%d).log 2>&1
```

---

### M2-P6: 定期実行セットアップ

| 項目 | 内容 |
|---|---|
| 対象ファイル | `logs/.gitkeep` / README |
| 実装内容 | `logs/` ディレクトリ作成 / cron 設定例を README に記載 / ログローテーション方針を記載 |
| 完了条件 | cron 設定を貼り付けるだけで定期実行できる手順が整っている |
| 依存 | M2-P5 |

**cron 設定例**

```cron
# scrape: 毎朝9時
0 9 * * * cd /path/to/idol-live-tracker && uv run python src/main.py scrape >> logs/$(date +\%Y-\%m-\%d).log 2>&1

# 週次サマリー: 毎週月曜09時（JST = UTC 0時）
0 0 * * 1 cd /path/to/idol-live-tracker && uv run python src/main.py summary >> logs/summary-$(date +\%Y-\%m-\%d).log 2>&1
```

---

## Milestone 3 — AI 解析・エンリッチメントによる完全自動化

**目標:** `base_url` だけ書けば動き、欠損フィールドを opt-in で AI 補完できる完成形

```
M2完了 → M3-P1 → M3-P2 → M3-P3 → M3-P4
                                  → M3-P5 → M3-P6
```

### M3-P1: ネットワークキャプチャ

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/analyzer/site_analyzer.py` |
| 実装内容 | Playwright の `request` / `response` イベントで XHR / Fetch ログを収集 / URL・メソッド・ボディ・ステータスを記録 |
| 完了条件 | avam-fc.com アクセス時に `POST /api/schedule/get` が捕捉される |
| 依存 | M2完了（DynamicFetcher の Playwright 環境を流用） |

---

### M3-P2: Claude API サイト解析

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/analyzer/site_analyzer.py` |
| 実装内容 | 解析プロンプト設計 / HTML 先頭 20,000 字 + ネットワークログを入力 / 出力を JSON Schema で固定 / `anthropic` SDK 呼び出し |
| 完了条件 | avam-fc.com の解析結果として正しい `navigation` / `selectors` / `response` が JSON で返る |
| 依存 | M3-P1 |

**Claude への入力**
- 現在の URL
- ページ HTML（先頭 20,000 字）
- キャプチャした XHR/Fetch リクエスト一覧
- 出力 JSON Schema（厳密に指定）

**Navigation タイプ優先順位（Claude への指示）**
```
api_endpoint > query_param > path_segment > pagination_links > single_page
```

---

### M3-P3: YAML 自動書き戻し

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/analyzer/config_writer.py` |
| 実装内容 | 解析結果を `artists.yaml` の該当アーティストにマージ / `analyzed_at` を更新 / 既存の `name` / `base_url` は保持 |
| 完了条件 | `analyzed_at` を含む完全な設定が YAML に反映される |
| 依存 | M3-P2 |

---

### M3-P4: analyze コマンド CLI 統合

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/main.py` |
| 実装内容 | `analyze` サブコマンド追加 / `--artist NAME` / `--force` オプション / 解析結果サマリ出力 |
| 完了条件 | `python main.py analyze --artist avam-fc` 1コマンドで解析〜YAML 更新が完結する |
| 依存 | M3-P3 |

---

### M3-P5: AI エンリッチメント（チケットサイト検索）

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/enricher/enricher.py` |
| 実装内容 | Notion から `取得ステータス: 一部未取得` のレコードを取得 / `"{title} {artist} {date}" site:eplus.jp` 等で検索 / Claude API で HTML から空欄フィールドを抽出 / Notion レコードを上書き更新 |
| 完了条件 | チケット料金・開始時刻・会場名などが補完され Notion レコードが更新される |
| 依存 | M3-P4 |

**検索対象（優先順）**

| サイト | 取得できる情報 |
|---|---|
| e+（イープラス） | 料金 / 開始時刻 / 会場 / 出演者 |
| チケットぴあ | 料金 / 開始時刻 / 会場 / 出演者 |
| ローソンチケット | 料金 / 開始時刻 / 会場 |

---

### M3-P6: enrich コマンド CLI 統合

| 項目 | 内容 |
|---|---|
| 対象ファイル | `src/main.py` |
| 実装内容 | `enrich` サブコマンド追加 / `--artist NAME` オプション / 補完件数サマリ出力 |
| 完了条件 | `python main.py enrich` で欠損フィールドが補完される |
| 依存 | M3-P5 |

---

## Pod 依存関係まとめ

```
M1-P1
  ├── M1-P2 ─────────────────────────────────────────────────────────┐
  ├── M1-P3 ── M1-P4（M1完了）                                       │
  │                │                                                   │
  │                ├── M2-P1 ── M2-P2（実機確認）                    │
  │                │         └── M2-P3 ── M2-P4                      │
  │                │                         │（M2完了）              │
  │                └── M2-P5 ── M2-P6        │                       │
  │                        └── M2-P8 ──┐    M3-P1 ── M3-P2          │
  └── M2-P7 ─────────────────────────┘│              │              │
                                        │            M3-P3 ── M3-P4 ─┤
                                        └─ (M2-P8依存)         │
                                                              M3-P5 ── M3-P6
```

---

## CLI コマンド全体像

| コマンド | 説明 | 実装 Pod |
|---|---|---|
| `uv run python src/main.py analyze [--artist NAME] [--force]` | サイト構造を解析して YAML を更新 | M3-P4 |
| `uv run python src/main.py scrape [--artist NAME] [--dry-run]` | イベントを収集して Notion 転記・Discord 通知 | M1-P4 |
| `uv run python src/main.py enrich [--artist NAME]` | 欠損フィールドを AI で補完（opt-in） | M3-P6 |

---

## リスク管理

| リスク | 該当 Pod | 対策 |
|---|---|---|
| avam-fc.com の API 仕様が変わる | M2-P2 | 実機確認を M2 最初に実施。失敗時は DynamicFetcher + DOM 解析にフォールバック |
| Claude の解析精度が低い | M3-P2 | Few-shot 例（avam-fc.com の正解設定）をプロンプトに含める |
| 未知のサイト構造で `type: unknown` になる | M3-P2 | YAML に `unknown` として書き戻し、手動編集を促すログを出す |
| チケットサイトの構造変更でエンリッチ失敗 | M3-P5 | 失敗しても既存レコードを壊さず `一部未取得` のまま保持 |
| Discord Webhook レート制限 | M2-P5 | 通知間に 0.5 秒の遅延を挟む |
