# Unit M2-P7: LocalStore（SQLite イベントキャッシュ）

## 概要

Notion の有無に関わらず動作する、ローカル SQLite ベースのイベント永続化層を実装する。
`scrape` コマンドの書き込み先として常に使用し、週次サマリーのデータソースになる。

---

## ブランチ・PR

```bash
git checkout -b feature/m2-local-store
gh pr create --title "feat: LocalStore — SQLite イベントキャッシュ（M2-P7）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/store/__init__.py` | 新規 |
| `src/store/local_store.py` | 新規 |
| `data/.gitkeep` | 新規（data/ ディレクトリを git 管理に追加） |
| `.gitignore` | 更新（`data/events.db` を除外） |

---

## 実装内容

### テーブル定義

```sql
CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    artist        TEXT    NOT NULL,
    title         TEXT    NOT NULL,
    date          TEXT,                  -- ISO 8601 (YYYY-MM-DD) or NULL
    start_time    TEXT    DEFAULT '',
    venue         TEXT    DEFAULT '',
    prefecture    TEXT    DEFAULT '',
    ticket_url    TEXT    DEFAULT '',
    ticket_price  TEXT    DEFAULT '',
    other_artists TEXT    DEFAULT '',
    poster_url    TEXT    DEFAULT '',
    source_url    TEXT    DEFAULT '',
    fetch_status  TEXT    DEFAULT 'タイトル・日付のみ',
    updated_at    TEXT    NOT NULL,      -- ISO 8601 datetime
    UNIQUE (artist, title, date)
);
```

### インターフェース

```python
class LocalStore:
    def __init__(self, db_path: str = "data/events.db") -> None: ...

    def upsert(self, event: LiveEvent) -> None:
        """重複キー (artist, title, date) で INSERT OR REPLACE。"""

    def upsert_many(self, events: list[LiveEvent]) -> None:
        """バルク upsert。トランザクションでまとめて実行。"""

    def get_upcoming(self, days: int = 14) -> list[LiveEvent]:
        """今日から days 日以内の未来イベントを date 昇順で返す。"""

    def get_all(self) -> list[LiveEvent]:
        """全レコードを date 昇順で返す。"""
```

### upsert のロジック

```python
# スクレイプデータを正として全フィールドを上書き
# ただし空文字のフィールドは既存値を保持する
INSERT INTO events (...) VALUES (...)
ON CONFLICT(artist, title, date) DO UPDATE SET
    venue        = CASE WHEN excluded.venue != '' THEN excluded.venue ELSE venue END,
    ticket_url   = CASE WHEN excluded.ticket_url != '' THEN excluded.ticket_url ELSE ticket_url END,
    ...
    updated_at   = excluded.updated_at
```

---

## 依存タスク

- task-1（M1-P1）: `LiveEvent` dataclass

## 並列実装可能なタスク

- M1-P2（NotionClient）と並列実装可能

---

## 完了条件

- [ ] `scrape --dry-run` では DB に書き込まれない
- [ ] `scrape` 実行後 `data/events.db` に全イベントが保存される
- [ ] 同一 `(artist, title, date)` を 2 回 upsert しても重複しない
- [ ] 空文字フィールドは既存値を保持する（上書き禁止）
- [ ] `get_upcoming(14)` が今日から 14 日以内のイベントのみ返す
- [ ] `data/events.db` が `.gitignore` に追加されている

---

## レビュー観点

- `data/` ディレクトリが存在しない場合に自動作成されるか
- SQLite の `UNIQUE` 制約で `date=NULL` のイベントが意図通り扱われるか（NULL は UNIQUE 制約外のため都度挿入になる点を確認）
- トランザクション未完了時にファイルが破損しないか
