"""SQLite を使ったライブイベントのローカルキャッシュ。(参照: docs/tasks/task-8/unit_1.md)

スクレイピング結果を永続化し、差分検出・重複排除に利用する。
重複判定キーは ``(artist, title, date)``。空文字フィールドは既存値を保持する。
"""

import os
import sqlite3
from datetime import date, datetime, timedelta, timezone

from src.models.event import LiveEvent

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    artist        TEXT    NOT NULL,
    title         TEXT    NOT NULL,
    date          TEXT,
    start_time    TEXT    DEFAULT '',
    venue         TEXT    DEFAULT '',
    prefecture    TEXT    DEFAULT '',
    ticket_url    TEXT    DEFAULT '',
    ticket_price  TEXT    DEFAULT '',
    other_artists TEXT    DEFAULT '',
    poster_url    TEXT    DEFAULT '',
    source_url    TEXT    DEFAULT '',
    fetch_status  TEXT    DEFAULT 'タイトル・日付のみ',
    updated_at    TEXT    NOT NULL,
    UNIQUE (artist, title, date)
);
"""

_UPSERT_SQL = """
INSERT INTO events (
    artist, title, date, start_time, venue, prefecture,
    ticket_url, ticket_price, other_artists, poster_url,
    source_url, fetch_status, updated_at
) VALUES (
    :artist, :title, :date, :start_time, :venue, :prefecture,
    :ticket_url, :ticket_price, :other_artists, :poster_url,
    :source_url, :fetch_status, :updated_at
)
ON CONFLICT(artist, title, date) DO UPDATE SET
    venue         = CASE WHEN excluded.venue != ''         THEN excluded.venue         ELSE venue         END,
    start_time    = CASE WHEN excluded.start_time != ''    THEN excluded.start_time    ELSE start_time    END,
    prefecture    = CASE WHEN excluded.prefecture != ''    THEN excluded.prefecture    ELSE prefecture    END,
    ticket_url    = CASE WHEN excluded.ticket_url != ''    THEN excluded.ticket_url    ELSE ticket_url    END,
    ticket_price  = CASE WHEN excluded.ticket_price != ''  THEN excluded.ticket_price  ELSE ticket_price  END,
    other_artists = CASE WHEN excluded.other_artists != '' THEN excluded.other_artists ELSE other_artists END,
    poster_url    = CASE WHEN excluded.poster_url != ''    THEN excluded.poster_url    ELSE poster_url    END,
    source_url    = CASE WHEN excluded.source_url != ''    THEN excluded.source_url    ELSE source_url    END,
    fetch_status  = CASE WHEN excluded.fetch_status != ''  THEN excluded.fetch_status  ELSE fetch_status  END,
    updated_at    = excluded.updated_at
"""

_SELECT_ALL_SQL = """
SELECT artist, title, date, start_time, venue, prefecture,
       ticket_url, ticket_price, other_artists, poster_url,
       source_url, fetch_status
FROM events
ORDER BY date ASC NULLS LAST
"""

_SELECT_UPCOMING_SQL = """
SELECT artist, title, date, start_time, venue, prefecture,
       ticket_url, ticket_price, other_artists, poster_url,
       source_url, fetch_status
FROM events
WHERE date IS NOT NULL
  AND date >= :today
  AND date <= :until
ORDER BY date ASC
"""


def _row_to_event(row: tuple) -> LiveEvent:
    """DB の行タプルを LiveEvent に変換する。

    Args:
        row: SELECT 結果の 12 要素タプル
              (artist, title, date, start_time, venue, prefecture,
               ticket_url, ticket_price, other_artists, poster_url,
               source_url, fetch_status)。

    Returns:
        LiveEvent インスタンス。
    """
    (
        artist, title, raw_date, start_time, venue, prefecture,
        ticket_url, ticket_price, other_artists, poster_url,
        source_url, fetch_status,
    ) = row

    parsed_date: date | None = (
        date.fromisoformat(raw_date) if raw_date is not None else None
    )

    event = LiveEvent(
        artist=artist,
        title=title,
        date=parsed_date,
        start_time=start_time or "",
        venue=venue or "",
        prefecture=prefecture or "",
        ticket_url=ticket_url or "",
        ticket_price=ticket_price or "",
        other_artists=other_artists or "",
        poster_url=poster_url or "",
        source_url=source_url or "",
    )
    # fetch_status は __post_init__ で自動算出されるが、DB の値を優先する
    object.__setattr__(event, "fetch_status", fetch_status or event.fetch_status)
    return event


class LocalStore:
    """SQLite を使ったライブイベントのローカルキャッシュ。

    重複判定キーは ``(artist, title, date)``。空文字フィールドは既存値を保持し、
    ``updated_at`` は upsert のたびに更新される。

    Attributes:
        db_path: SQLite ファイルのパス。存在しない場合は自動作成される。
    """

    def __init__(self, db_path: str = "data/events.db") -> None:
        """LocalStore を初期化し、テーブルを作成する。

        Args:
            db_path: SQLite ファイルのパス。親ディレクトリが存在しない場合は自動作成する。
        """
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE_SQL)

    def _connect(self) -> sqlite3.Connection:
        """sqlite3 コネクションを返す。

        Returns:
            WAL モードを有効にした sqlite3.Connection。
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    @staticmethod
    def _now_iso() -> str:
        """現在日時を ISO 8601 文字列で返す。

        Returns:
            UTC 日時文字列 (例: ``2026-05-05T12:34:56+00:00``)。
        """
        return datetime.now(tz=timezone.utc).isoformat()

    def _event_to_params(self, event: LiveEvent) -> dict:
        """LiveEvent を SQL パラメータ dict に変換する。

        Args:
            event: 変換対象のイベント。

        Returns:
            名前付きパラメータの dict。
        """
        return {
            "artist": event.artist,
            "title": event.title,
            "date": str(event.date) if event.date is not None else None,
            "start_time": event.start_time,
            "venue": event.venue,
            "prefecture": event.prefecture,
            "ticket_url": event.ticket_url,
            "ticket_price": event.ticket_price,
            "other_artists": event.other_artists,
            "poster_url": event.poster_url,
            "source_url": event.source_url,
            "fetch_status": event.fetch_status,
            "updated_at": self._now_iso(),
        }

    def upsert(self, event: LiveEvent) -> None:
        """重複キー ``(artist, title, date)`` で INSERT OR REPLACE する。

        空文字フィールドは既存値を保持する。``updated_at`` は常に更新される。

        Args:
            event: 保存対象の LiveEvent。
        """
        with self._connect() as conn:
            conn.execute(_UPSERT_SQL, self._event_to_params(event))

    def upsert_many(self, events: list[LiveEvent]) -> None:
        """バルク upsert。トランザクションでまとめて実行する。

        Args:
            events: 保存対象の LiveEvent リスト。空リストの場合は何もしない。
        """
        if not events:
            return
        params = [self._event_to_params(e) for e in events]
        with self._connect() as conn:
            conn.executemany(_UPSERT_SQL, params)

    def upsert_many_diff(
        self, events: list[LiveEvent]
    ) -> tuple[list[LiveEvent], list[tuple[LiveEvent, dict]]]:
        """upsert を実行し、新規と更新を分けて返す。

        重複判定キー ``(artist, title, date)`` が DB に存在しなければ新規、
        存在していてフィールドに変化があれば更新とみなす。

        Args:
            events: 保存対象の LiveEvent リスト。

        Returns:
            ``(created, updated)`` のタプル。
            ``created``: 今回初めて登録したイベント。
            ``updated``: ``[(event, diff), ...]`` — 変化したフィールド名と新値の辞書を伴う更新イベント。
        """
        if not events:
            return [], []

        _COMPARABLE_FIELDS = (
            "venue", "start_time", "ticket_url", "ticket_price",
            "other_artists", "poster_url", "source_url",
        )

        existing: dict[tuple, LiveEvent] = {
            e.identity_key(): e for e in self.get_all()
        }

        created: list[LiveEvent] = []
        updated: list[tuple[LiveEvent, dict]] = []

        for event in events:
            key = event.identity_key()
            if key not in existing:
                created.append(event)
            else:
                prev = existing[key]
                diff = {
                    f: getattr(event, f)
                    for f in _COMPARABLE_FIELDS
                    if getattr(event, f) and getattr(event, f) != getattr(prev, f)
                }
                if diff:
                    updated.append((event, diff))

        self.upsert_many(events)
        return created, updated

    def get_upcoming(self, days: int = 14) -> list[LiveEvent]:
        """今日から ``days`` 日以内の未来イベントを date 昇順で返す。

        ``date IS NULL`` のイベントは除外される。

        Args:
            days: 取得対象の日数（今日を含む）。デフォルト 14 日。

        Returns:
            date 昇順の LiveEvent リスト。
        """
        today = date.today()
        until = today + timedelta(days=days)
        with self._connect() as conn:
            rows = conn.execute(
                _SELECT_UPCOMING_SQL,
                {"today": str(today), "until": str(until)},
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def get_all(self) -> list[LiveEvent]:
        """全レコードを date 昇順で返す。

        ``date IS NULL`` のレコードは末尾に並ぶ。

        Returns:
            date 昇順（NULL 末尾）の LiveEvent リスト。
        """
        with self._connect() as conn:
            rows = conn.execute(_SELECT_ALL_SQL).fetchall()
        return [_row_to_event(row) for row in rows]
