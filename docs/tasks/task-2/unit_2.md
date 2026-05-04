# Unit 1-3: HTML スクレイパー（single_page）

## 概要
`single_page` タイプのサイトを CSS セレクタでスクレイピングする最小実装。
Unit 1-2 と並列実装可能。Unit 1-4 の CLI から呼ばれる。

---

## ブランチ・PR

```bash
git checkout -b feature/m1-html-scraper
# 実装後
gh pr create --title "feat: HTML スクレイパー基底実装（single_page）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/scrapers/__init__.py` | 新規 |
| `src/scrapers/base.py` | 新規 |
| `src/scrapers/generic.py` | 新規 |

---

## 実装内容

### BaseScraper（src/scrapers/base.py）

```python
class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, config: ArtistConfig) -> list[LiveEvent]:
        ...
```

### GenericScraper（src/scrapers/generic.py）

```python
class GenericScraper(BaseScraper):
    def scrape(self, config: ArtistConfig) -> list[LiveEvent]:
        """このタスクでは single_page のみ対応。他タイプは M2 で追加"""

    def _fetch_static(self, url: str) -> Page:
        """Scrapling Fetcher.get()"""

    def _parse_events(self, page: Page, selectors: dict) -> list[LiveEvent]:
        """CSS セレクタで event_list を取得し、各フィールドを抽出"""
```

---

## 統合後のインターフェース

```python
from src.scrapers.generic import GenericScraper

scraper = GenericScraper()
events: list[LiveEvent] = scraper.scrape(artist_config)
```

---

## 人間の介入が必要な手順

テスト用に `config/artists.yaml` へ `navigation.type: single_page` の実在サイトを1件追加する。
（静的 HTML でスケジュールが掲載されているサイトを選ぶこと）

---

## 依存タスク

- Unit 1-1（LiveEvent / ArtistConfig 型定義）

## 並列実装可能なタスク

- Unit 1-2（Notion Client）と並列着手可能

---

## 完了条件

- [ ] `single_page` タイプのサイトから `list[LiveEvent]` が返る
- [ ] セレクタで要素が見つからない場合、フィールドを `""` として処理を継続する
- [ ] `--dry-run` 相当の呼び出しでイベント一覧がターミナルに出力される

---

## レビュー観点

- セレクタ未検出時に例外を raise せず空文字でスキップしているか
- `artist` フィールドが config の `name` から正しく埋まっているか
- `fetch_status` が取得できたフィールド数に応じて正しく設定されているか
- Scrapling の `Fetcher.get()` がタイムアウト時にログを出してスキップするか
