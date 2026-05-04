# Unit 2-2: api_endpoint 対応（avam-fc.com 実機確認）

## 概要
`api_endpoint` タイプのサイト（avam-fc.com）に対応する。
JSON レスポンスを `LiveEvent` にマッピングし、詳細ページから追加情報を取得する。
**M2 の中で最もリスクが高いタスク。最優先で着手すること。**

---

## ブランチ・PR

```bash
git checkout -b feature/m2-api-endpoint-scraper
# 実装後
gh pr create --title "feat: api_endpoint タイプスクレイピング（avam-fc.com 実機確認）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/scrapers/generic.py` | 更新 |

---

## 実装内容

`GenericScraper` に以下メソッドを追加：

```python
def _call_api(self, target: ScrapeTarget) -> list[dict]:
    """POST リクエストを送信し JSON を返す"""

def _map_api_response(
    self, raw: list[dict], mapping: ResponseMapping, artist: str
) -> list[LiveEvent]:
    """response.mapping 設定に従い dict → LiveEvent 変換"""

def _fetch_detail(
    self, event: LiveEvent, detail_config: DetailConfig
) -> LiveEvent:
    """detail.enabled: true 時に詳細ページへアクセスし追加フィールドを補完"""
```

`scrape()` 内で `target.api` がある場合は `_call_api` → `_map_api_response` → （`detail.enabled` なら）`_fetch_detail` の順で処理する。

---

## 統合後のインターフェース

task-5/unit_1 完了後も `GenericScraper.scrape()` のインターフェースは変わらない：

```python
events: list[LiveEvent] = GenericScraper().scrape(artist_config)
```

呼び出し側（main.py）の変更は不要。

---

## 人間の介入が必要な手順

1. `config/artists.yaml` に avam-fc.com の設定を記述する：

```yaml
- name: avam-fc
  base_url: https://avam-fc.com/schedule
  fetch:
    dynamic: false
  navigation:
    type: api_endpoint
    endpoint: /api/schedule/get
    method: POST
    body_template:
      start: "{month_start}"
      end: "{month_end}"
    range_months: 3
  response:
    format: json_array
    array_path: ""
    mapping:
      id: id
      title: title
      date: reception_date
      date_format: "%Y-%m-%d"
  detail:
    enabled: true
    url_pattern: "{base_url}/detail/{id}?d={date}"
    selectors:
      venue: ".venue-name"
      start_time: ".start-time"
      ticket_url: "a.ticket::attr(href)"
      other_artists: ".performers"
      poster_url: "img.poster::attr(src)"
```

2. `python main.py scrape --artist avam-fc --dry-run` で実機確認する

---

## 依存タスク

- task-4/unit_1（M2-P1 URLGenerator）

## 並列実装可能なタスク

- task-5/unit_2（DynamicFetcher 統合）と同時着手可能

---

## 完了条件

- [ ] avam-fc.com から `list[LiveEvent]` が取得できる（実機確認）
- [ ] `detail.enabled: true` 時に詳細ページのフィールドが補完されている
- [ ] `python main.py scrape --artist avam-fc` で Notion に転記される

---

## レビュー観点

- `response.mapping` の `date_format` で日付パースが正しいか
- 詳細ページ取得が失敗したとき、メインページ取得分だけで処理を継続するか
- API レスポンスの `id` が `detail.url_pattern` に正しく埋め込まれているか
- 詳細ページの CSS セレクタが存在しない場合、空文字で継続するか
