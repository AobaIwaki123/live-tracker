# Unit 1-2: Notion Client

## 概要
Notion API の CRUD ラッパーを実装する。
スクレイプデータを正とした差分検出・フィールド単位更新を担い、Unit 1-4 の scrape コマンドと Unit 2-5 の Discord 通知に使われる。

---

## ブランチ・PR

```bash
git checkout -b feature/m1-notion-client
# 実装後
gh pr create --title "feat: Notion Client（作成・差分更新）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/notion/__init__.py` | 新規 |
| `src/notion/client.py` | 新規 |

---

## 実装内容

```python
class NotionClient:
    def fetch_all(self) -> dict[tuple, NotionRecord]:
        """DB 全件取得。キー: (artist, title, date)"""

    def create(self, event: LiveEvent) -> str:
        """新規ページ作成。page_id を返す"""

    def update(self, page_id: str, diff: dict[str, Any]) -> None:
        """差分フィールドのみ上書き"""

    def upsert_events(
        self, events: list[LiveEvent]
    ) -> tuple[list[LiveEvent], list[tuple[LiveEvent, dict]]]:
        """
        Returns:
            created: 新規作成されたイベントリスト
            updated: (event, diff_fields) のリスト
        """
```

**差分検出ルール:**
- `existing[field] != scraped[field]` かつ `scraped[field] != ""` → 上書き対象
- スクレイプデータを正とし、手動入力も上書きする

---

## 統合後のインターフェース

```python
from src.notion.client import NotionClient

client = NotionClient()
created, updated = client.upsert_events(events)
# created: list[LiveEvent]  → Discord 新規通知用
# updated: list[(LiveEvent, dict)]  → Discord 更新通知用
```

---

## 人間の介入が必要な手順

1. **Notion Integration 作成**
   - https://www.notion.so/my-integrations でインテグレーション作成
   - `NOTION_TOKEN` を `.env` に設定

2. **Notion DB 作成**
   - 以下スキーマで DB を手動作成：

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

3. **DB をインテグレーションに共有**
   - DB を開き「接続を追加」から作成したインテグレーションを追加
   - DB URL から `NOTION_DATABASE_ID` を取得して `.env` に設定

---

## 依存タスク

- Unit 1-1（LiveEvent 型定義）

## 並列実装可能なタスク

- Unit 1-3（HTML スクレイパー）と並列着手可能

---

## 完了条件

- [ ] Notion DB に `LiveEvent` 1件を作成できる
- [ ] `fetch_all()` で既存レコードが `(artist, title, date)` をキーとした dict で取れる
- [ ] 同じイベントを再度 `upsert_events()` したとき `updated` が空になる
- [ ] フィールドを変えて `upsert_events()` したとき差分フィールドのみ更新される

---

## レビュー観点

- `fetch_all()` が DB に大量レコードあっても全件取得できるか（Notion API ページネーション対応）
- `update()` が `fetch_status` を正しく再計算して更新しているか
- API エラー時にリトライせずスキップし、ログに記録しているか
- `NOTION_TOKEN` / `NOTION_DATABASE_ID` 未設定時に分かりやすいエラーを出すか
