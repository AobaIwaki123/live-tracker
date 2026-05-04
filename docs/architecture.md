# アーキテクチャ図 — idol-live-tracker

## 1. 2 フェーズ構成の全体像

本ツールは **analyze（解析）** と **scrape（収集）** の 2 フェーズで動作する。
人間は `base_url` のみを指定すればよく、サイト構造の調査・設定生成は AI が行う。

```mermaid
flowchart LR
    subgraph Human["人間の作業"]
        H1[base_url を\nYAMLに記載]
    end

    subgraph Phase1["Phase 1: analyze コマンド（初回 or --force 時）"]
        A1[DynamicFetcher\nページ取得 +\nXHR キャプチャ]
        A2[Claude API\n構造解析]
        A3[YAML 設定\n自動生成]
        A1 --> A2 --> A3
    end

    subgraph Phase2["Phase 2: scrape コマンド（定期実行）"]
        S1[URLGenerator\nURL/APIリクエスト生成]
        S2[GenericScraper\n情報収集]
        S3[LiveEvent\nリスト生成]
        S4[NotionClient\n差分書き込み]
        S1 --> S2 --> S3 --> S4
    end

    H1 -->|base_url| Phase1
    Phase1 -->|navigation + selectors| Phase2
    Phase2 -->|新規イベントのみ| DB[(Notion DB)]
```

---

## 2. Navigation タイプ判定フロー（analyze フェーズ）

```mermaid
flowchart TD
    START([base_url 受取]) --> FETCH[DynamicFetcher でページ取得\n+ XHR/Fetch ネットワークキャプチャ]
    FETCH --> AI{Claude API\n構造解析}

    AI -->|XHRで schedule系APIを検出| API_TYPE[type: api_endpoint\nendpoint / method / body抽出]
    AI -->|URL に ?d= / ?month= 等| QP_TYPE[type: query_param\nparam / format 抽出]
    AI -->|URLパスに年月| PS_TYPE[type: path_segment\npattern 抽出]
    AI -->|next/prevリンクあり| PL_TYPE[type: pagination_links\nnext_selector 抽出]
    AI -->|上記いずれでもない| SP_TYPE[type: single_page]

    API_TYPE --> YAML_OUT
    QP_TYPE --> YAML_OUT
    PS_TYPE --> YAML_OUT
    PL_TYPE --> YAML_OUT
    SP_TYPE --> YAML_OUT

    YAML_OUT([YAML 設定ファイルへ書き戻し\n人間がレビュー])
```

---

## 3. Navigation タイプ別 URL/リクエスト生成（scrape フェーズ）

```mermaid
flowchart LR
    CONFIG[artists.yaml\nnavigation.type] --> UG[URLGenerator]

    UG -->|single_page| URL1["[base_url]"]
    UG -->|query_param| URL2["[base_url?d=2026-05-01,\n base_url?d=2026-06-01, ...]"]
    UG -->|path_segment| URL3["[base_url/2026/05,\n base_url/2026/06, ...]"]
    UG -->|pagination_links| URL4["[base_url]\n→ next リンクを追跡"]
    UG -->|api_endpoint| REQ["[POST /api/schedule/get\n {start:..., end:...} × N ヶ月]"]

    URL1 & URL2 & URL3 & URL4 --> HTML_SCRAPER[HTML スクレイパー\nCSSセレクタで抽出]
    REQ --> API_CLIENT[API クライアント\nJSON レスポンス解釈]

    HTML_SCRAPER --> EVENT[LiveEvent list]
    API_CLIENT --> EVENT
```

---

## 4. シーケンス図 — analyze コマンド

```mermaid
sequenceDiagram
    actor User
    participant CLI as main.py analyze
    participant Fetcher as DynamicFetcher
    participant Site as アーティスト公式サイト
    participant Claude as Claude API
    participant Config as artists.yaml

    User->>CLI: python main.py analyze --artist avam-fc
    CLI->>Config: base_url 読み込み
    Config-->>CLI: https://avam-fc.com/schedule

    CLI->>Fetcher: fetch(url, capture_network=True)
    Fetcher->>Site: Playwright でブラウザ起動
    Site-->>Fetcher: HTML + XHRログ
    Fetcher-->>CLI: (html, network_log)

    CLI->>Claude: analyze_site(html, network_log, base_url)
    Note over Claude: HTML・ネットワークログを解析し<br/>navigation/selectors/response を推論
    Claude-->>CLI: SiteConfig (JSON)

    CLI->>Config: navigation + selectors を YAML に書き戻し
    CLI->>User: 解析結果サマリ出力（レビューを促す）
```

---

## 5. シーケンス図 — scrape コマンド

```mermaid
sequenceDiagram
    actor User
    participant CLI as main.py scrape
    participant UG as URLGenerator
    participant Scraper as GenericScraper
    participant Site as アーティスト公式サイト
    participant Notion as NotionClient
    participant DB as Notion Database

    User->>CLI: python main.py scrape [--artist X] [--dry-run]

    loop 各アーティスト
        CLI->>UG: generate_targets(artist_config)
        UG-->>CLI: list[ScrapeTarget]

        loop 各ターゲット（月ごと）
            CLI->>Scraper: scrape_target(target)
            Scraper->>Site: HTTP / API Request
            Site-->>Scraper: HTML / JSON
            Scraper-->>CLI: list[LiveEvent]
        end

        alt --dry-run
            CLI->>User: ターミナル出力
        else 通常実行
            CLI->>Notion: append_events(events)
            Notion->>DB: 既存キー取得
            DB-->>Notion: existing_keys
            Notion->>Notion: 差分フィルタリング
            Notion->>DB: 新規イベント書き込み
            Notion-->>CLI: 書き込み件数
        end
    end

    CLI->>User: 実行サマリ出力
```

---

## 6. ディレクトリ構造

```
idol-live-tracker/
├── docs/
│   ├── requirements.md      ← 要件定義書
│   ├── basic-design.md      ← 基本設計書
│   └── architecture.md      ← 本ファイル（アーキテクチャ図）
├── src/
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── site_analyzer.py ← AI サイト解析（Claude API）
│   │   └── config_writer.py ← 解析結果を YAML へ書き戻す
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py          ← BaseScraper (ABC)
│   │   ├── url_generator.py ← navigation config → URL/リクエスト生成
│   │   └── generic.py       ← GenericScraper
│   ├── notion/
│   │   ├── __init__.py
│   │   └── client.py        ← NotionClient
│   ├── models/
│   │   ├── __init__.py
│   │   └── event.py         ← LiveEvent dataclass
│   └── main.py              ← CLI エントリーポイント
├── config/
│   └── artists.yaml         ← base_url のみ記載して analyze で自動補完
├── .env.example
└── pyproject.toml
```

---

## 7. 技術スタック

| レイヤー | 採用技術 | 理由 |
|---|---|---|
| サイト解析 | Claude API (claude-sonnet-4-6) | HTML + ネットワークログから構造を推論 |
| スクレイピング（静的） | Scrapling Fetcher | 軽量・TLS フィンガープリント偽装 |
| スクレイピング（動的） | Scrapling DynamicFetcher | Playwright ベース、JS レンダリング対応 |
| Notion 連携 | notion-client (公式 SDK) | 公式サポート、型安全 |
| 設定管理 | PyYAML + python-dotenv | 設定とシークレットを分離 |
| 実行言語 | Python 3.10+ | Scrapling / match 文の最低要件 |
