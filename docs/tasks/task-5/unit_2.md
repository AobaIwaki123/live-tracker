# Unit 2-3: DynamicFetcher 統合

## 概要
`fetch.dynamic: true` のサイトに Playwright ベースの `DynamicFetcher` を使う。
Unit 2-2 と並列着手可能。Unit 2-4（pagination_links）の前提。

---

## ブランチ・PR

```bash
git checkout -b feature/m2-dynamic-fetcher
# 実装後
gh pr create --title "feat: DynamicFetcher 統合（JS レンダリング対応）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/scrapers/generic.py` | 更新 |
| `README.md` | 更新（Playwright セットアップ手順追加） |

---

## 実装内容

`_fetch_static()` に加えて `_fetch_dynamic()` を追加し、`config.fetch.dynamic` で切り替える：

```python
def _fetch_page(self, url: str, dynamic: bool) -> Page:
    if dynamic:
        return DynamicFetcher.fetch(url)
    return Fetcher.get(url)
```

---

## 統合後のインターフェース

`GenericScraper.scrape()` のインターフェースは変わらない。
`artists.yaml` の `fetch.dynamic` フラグのみで切り替わる。

---

## 人間の介入が必要な手順

初回のみ Playwright のブラウザをインストールする：

```bash
pip install scrapling[all]
scrapling install  # または playwright install chromium
```

---

## 依存タスク

- Unit 2-1（URLGenerator）

## 並列実装可能なタスク

- Unit 2-2（api_endpoint 対応）と並列着手可能

---

## 完了条件

- [ ] `fetch.dynamic: true` のサイトで JS レンダリング後の HTML が取得できる
- [ ] `fetch.dynamic: false` のサイトで従来の静的取得が動作し続ける
- [ ] README にセットアップ手順が記載されている

---

## レビュー観点

- `DynamicFetcher` がタイムアウトしたときにリトライせずスキップしているか
- `DynamicFetcher` と `Fetcher` で返る `Page` オブジェクトのインターフェースが統一されているか（`_parse_events` が両方に対応できるか）
