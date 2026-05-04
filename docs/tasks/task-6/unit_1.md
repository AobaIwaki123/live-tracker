# Unit 2-4: pagination_links 対応

## 概要
`navigation.type: pagination_links` のサイトで次ページリンクを辿って全件収集する。
Unit 2-3 完了後に着手する。

---

## ブランチ・PR

```bash
git checkout -b feature/m2-pagination-links
# 実装後
gh pr create --title "feat: pagination_links タイプ対応（次ページリンク追跡）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/scrapers/generic.py` | 更新 |

---

## 実装内容

`ScrapeTarget.follow_next = True` のとき、`_follow_next_links()` でページを再帰的に収集：

```python
def _follow_next_links(
    self, start_url: str, next_selector: str, max_pages: int
) -> list[LiveEvent]:
    events = []
    url = start_url
    for _ in range(max_pages):
        page = self._fetch_page(url, dynamic=config.fetch.dynamic)
        events.extend(self._parse_events(page, config.selectors))
        next_url = page.css(next_selector + "::attr(href)").get()
        if not next_url:
            break
        url = next_url
    return events
```

---

## 統合後のインターフェース

`GenericScraper.scrape()` のインターフェースは変わらない。

---

## 人間の介入が必要な手順

`artists.yaml` に `pagination_links` タイプの実在サイトを1件追加して動作確認する。

---

## 依存タスク

- Unit 2-3（DynamicFetcher 統合）

## 並列実装可能なタスク

なし（Unit 2-3 完了後に着手）

---

## 完了条件

- [ ] `next_selector` で次ページ URL が取得でき、全ページのイベントが収集される
- [ ] 次ページリンクがなくなったとき（最終ページ）で正常終了する
- [ ] `max_pages` を超えたときに警告ログを出して打ち切る

---

## レビュー観点

- 無限ループに入らないか（`max_pages` が確実に機能しているか）
- 相対 URL（`/schedule?page=2`）を絶対 URL に変換しているか
- 各ページで同じイベントが重複取得された場合に `identity_key` で重複除去されるか
