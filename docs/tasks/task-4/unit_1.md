# Unit 2-1: URLGenerator

## 概要
`navigation.type` に応じた URL / API リクエストリストを生成する。
M2 の他タスク（Unit 2-2, 2-3）の前提となるコンポーネント。
Unit 2-5（Discord）と並列着手可能。

---

## ブランチ・PR

```bash
git checkout -b feature/m2-url-generator
# 実装後
gh pr create --title "feat: URLGenerator（navigation タイプ別 URL 生成）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/scrapers/url_generator.py` | 新規 |

---

## 実装内容

```python
@dataclass
class ScrapeTarget:
    url: str | None = None
    api: ApiRequest | None = None
    follow_next: bool = False   # pagination_links 用

@dataclass
class ApiRequest:
    url: str
    method: str
    body: dict

def generate_targets(config: ArtistConfig) -> list[ScrapeTarget]:
    nav = config.navigation
    months = [today + relativedelta(months=i) for i in range(nav.range_months)]

    match nav.type:
        case "single_page":   ...
        case "query_param":   ...
        case "path_segment":  ...
        case "pagination_links": ...
        case "api_endpoint":  ...
```

`{month_start}` / `{month_end}` プレースホルダーは各月の初日・末日の `YYYY-MM-DD` に展開する。

---

## 統合後のインターフェース

```python
from src.scrapers.url_generator import generate_targets, ScrapeTarget

targets: list[ScrapeTarget] = generate_targets(artist_config)
# target.url  → HTML スクレイピング用 URL
# target.api  → API リクエスト情報
```

---

## 人間の介入が必要な手順

なし

---

## 依存タスク

- task-3/unit_1（M1-P4 CLI 骨格）

## 並列実装可能なタスク

- task-4/unit_2（Discord Notifier）と同時着手可能

---

## 完了条件

- [ ] `single_page` → 1件のターゲットが返る
- [ ] `query_param` → `range_months` 分の URL が返る
- [ ] `path_segment` → パターン展開された URL が返る
- [ ] `api_endpoint` → 各月のボディが `{month_start}`/`{month_end}` 展開された `ApiRequest` が返る

---

## レビュー観点

- 月末日の計算が正確か（2月末など）
- `range_months` が 0 以下の場合の挙動
- `pagination_links` タイプが `follow_next=True` の1件のみ返しているか（ページ追跡は Scraper 側）
