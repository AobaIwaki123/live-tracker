"""Discord 週次サマリー通知モジュール。(参照: docs/tasks/task-8/unit_2.md)"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import date, timedelta

import requests

from src.models.event import LiveEvent

logger = logging.getLogger(__name__)

_MAX_MESSAGE_LENGTH = 2000
_SEPARATOR_HEAVY = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
_SEPARATOR_LIGHT = "─────────────────────────────"

_WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]

_TICKET_SITE_NAMES: dict[str, str] = {
    "eplus.jp": "e+",
    "pia.jp": "チケットぴあ",
    "t.pia.jp": "チケットぴあ",
    "l-tike.com": "ローチケ",
    "lawson-ticket.com": "ローチケ",
    "ticket.rakuten.co.jp": "楽天チケット",
    "yahoo-ticket.jp": "Yahooチケット",
    "zaiko.io": "ZAIKO",
}


def _weekday_ja(d: date) -> str:
    """Return the Japanese weekday string for a given date.

    Args:
        d: The date to get the weekday for.

    Returns:
        Japanese weekday string (月〜日).
    """
    return _WEEKDAY_JA[d.weekday()]


def _format_date_short(d: date) -> str:
    """Format date as M/D (曜) with no zero-padding.

    Args:
        d: The date to format.

    Returns:
        Formatted date string like "5/10 (土)".
    """
    return f"{d.month}/{d.day} ({_weekday_ja(d)})"


def _format_date_full(d: date) -> str:
    """Format date as YYYY/MM/DD (曜).

    Args:
        d: The date to format.

    Returns:
        Formatted date string like "2026/05/10 (土)".
    """
    return f"{d.year}/{d.month:02d}/{d.day:02d} ({_weekday_ja(d)})"


def _ticket_site_name(url: str) -> str:
    """Infer ticket site display name from a URL.

    Args:
        url: The ticket URL.

    Returns:
        Display name like "e+" or the domain as fallback.
    """
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lstrip("www.")
        for key, label in _TICKET_SITE_NAMES.items():
            if host == key or host.endswith("." + key):
                return label
        return host or "チケット"
    except Exception:  # noqa: BLE001
        return "チケット"


def _parse_start_time(start_time: str) -> tuple[str, str]:
    """Parse a start_time string into (open_time, start_time) pair.

    Supported formats:
    - ``"HH:MM"``              → open="", start="HH:MM"
    - ``"OPEN HH:MM"``         → open="HH:MM", start=""
    - ``"START HH:MM"``        → open="", start="HH:MM"
    - ``"OPEN HH:MM / START HH:MM"``  → open="HH:MM", start="HH:MM"
    - ``"OPEN HH:MM ／ START HH:MM"`` → same with full-width slash

    Args:
        start_time: Raw start_time value from LiveEvent.

    Returns:
        Tuple of (open_str, start_str). Empty string when not present.
    """
    if not start_time:
        return "", ""

    # Match "OPEN HH:MM / START HH:MM" (half-width or full-width slash)
    m = re.match(
        r"OPEN\s+(\d{1,2}:\d{2})\s*[/／]\s*START\s+(\d{1,2}:\d{2})",
        start_time,
        re.IGNORECASE,
    )
    if m:
        return m.group(1), m.group(2)

    # Match "OPEN HH:MM"
    m = re.match(r"OPEN\s+(\d{1,2}:\d{2})", start_time, re.IGNORECASE)
    if m:
        return m.group(1), ""

    # Match "START HH:MM"
    m = re.match(r"START\s+(\d{1,2}:\d{2})", start_time, re.IGNORECASE)
    if m:
        return "", m.group(1)

    # Plain "HH:MM" — treat as START
    m = re.match(r"(\d{1,2}:\d{2})$", start_time.strip())
    if m:
        return "", m.group(1)

    # Fallback: return as start
    return "", start_time.strip()


class WeeklySummaryNotifier:
    """Discord Webhook を使って直近のライブ予定を週次サマリーとして送信するクラス。

    イベントを日付・週でグループ化し、フォーマット仕様に従ってテキストブロックを
    生成して Discord に POST する。2000 文字を超える場合は週単位で分割送信する。

    Attributes:
        webhook_url: Discord Webhook URL。空文字の場合は送信をスキップする。
    """

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send(
        self,
        events: list[LiveEvent],
        new_count: int | None = None,
        updated_count: int | None = None,
    ) -> None:
        """イベントリストを日付・週でグルーピングして Discord へ送信する。

        2000 文字を超える場合は週単位で分割して複数回送信する。
        events が空の場合は何もしない。

        Args:
            events: 送信するライブイベントのリスト。date が None のものはスキップされる。
            new_count: フッターに表示する新規件数。None の場合は events の件数を使う。
            updated_count: フッターに表示する更新件数。None の場合は 0 を使う。
        """
        if not events:
            return

        # Filter out events without a date and sort by date
        dated = sorted(
            [e for e in events if e.date is not None],
            key=lambda e: e.date,  # type: ignore[arg-type]
        )
        if not dated:
            return

        today = date.today()
        week_groups = self._group_by_week(dated, today)

        if new_count is None:
            new_count = len(dated)
        if updated_count is None:
            updated_count = 0

        footer = self._format_footer(new_count, updated_count, today)

        # Build per-week blocks
        week_nums = sorted(week_groups.keys())
        week_blocks: list[str] = [
            self._format_week_block(wn, week_groups[wn]) for wn in week_nums
        ]

        # Send messages, splitting at week boundaries when > 2000 chars
        current_parts: list[str] = []
        current_len = 0

        for block in week_blocks:
            block_len = len(block) + 1  # +1 for joining newline
            if current_parts and current_len + block_len > _MAX_MESSAGE_LENGTH:
                self._post("\n".join(current_parts))
                current_parts = [block]
                current_len = len(block)
            else:
                current_parts.append(block)
                current_len += block_len

        # Last batch with footer
        if current_parts:
            message = "\n".join(current_parts) + "\n" + footer
            self._post(message)

    def _group_by_week(
        self,
        events: list[LiveEvent],
        today: date,
    ) -> dict[int, list[LiveEvent]]:
        """イベントを相対週番号（1始まり）でグループ化する。

        Week N の N は today が属する週を 1 として、1 週 = 7 日で計算する。
        today の週の月曜日を week_start として、各イベントの date からの差分で
        週番号を決定する。

        Args:
            events: date が None でないライブイベントのリスト（日付昇順を想定）。
            today: 送信日（相対週の基準）。

        Returns:
            ``{week_num: [LiveEvent, ...]}`` の辞書。week_num は 1 始まり。
        """
        # Monday of today's week
        week_start = today - timedelta(days=today.weekday())

        groups: dict[int, list[LiveEvent]] = defaultdict(list)
        for event in events:
            assert event.date is not None
            delta_days = (event.date - week_start).days
            # week_num: 1-indexed; events before week_start fall into week 1 (clamp)
            week_num = max(1, delta_days // 7 + 1)
            groups[week_num].append(event)

        return dict(groups)

    def _format_week_block(
        self,
        week_num: int,
        events: list[LiveEvent],
    ) -> str:
        """1 週分のテキストブロックを生成する。

        ブロック構造:
        ``▍ Week N  M/D (曜) 〜 M/D (曜)``
        ``━━━━━━━━━━━━━━━━━━━━━━━━━━━━━``
        （空行）
        日付ブロック × n

        Args:
            week_num: 相対週番号（1 始まり）。
            events: この週に属するイベントのリスト（日付昇順）。

        Returns:
            週ブロックのテキスト文字列。
        """
        dates_in_week = sorted({e.date for e in events if e.date is not None})
        first_date = dates_in_week[0]
        last_date = dates_in_week[-1]

        header = (
            f"▍ Week {week_num}  {_format_date_short(first_date)}"
            f" 〜 {_format_date_short(last_date)}"
        )
        lines: list[str] = [header, _SEPARATOR_HEAVY, ""]

        # Group events by date
        date_groups: dict[date, list[LiveEvent]] = defaultdict(list)
        for event in events:
            if event.date is not None:
                date_groups[event.date].append(event)

        for d in sorted(date_groups.keys()):
            lines.append(f"📅 {_format_date_full(d)}")
            lines.append(_SEPARATOR_LIGHT)
            day_events = date_groups[d]
            for idx, event in enumerate(day_events):
                lines.append(self._format_event(event))
                if idx < len(day_events) - 1:
                    lines.append("")  # blank line between events on same day
            lines.append("")  # blank line between dates

        return "\n".join(lines).rstrip()

    def _format_event(self, event: LiveEvent) -> str:
        """1 イベント分の行を生成する。

        フォーマット:
        ```
        🎤 <アーティスト名>
        　📍 <会場名>（<都道府県>）
        　🕐 OPEN HH:MM ／ START HH:MM    # 時刻がある場合のみ
        　👥 <出演者>                       # other_artists がある場合のみ
        　🎫 <サイト名>  <URL>  💴 ¥<金額>  # ticket_url がある場合
        ```

        Args:
            event: フォーマット対象のライブイベント。

        Returns:
            イベント行のテキスト文字列（末尾に改行なし）。
        """
        INDENT = "　"  # full-width space for visual indent

        lines: list[str] = [f"🎤 {event.artist}"]

        # Venue line (always shown)
        venue_str = event.venue or "会場未定"
        pref_str = f"（{event.prefecture}）" if event.prefecture else ""
        lines.append(f"{INDENT}📍 {venue_str}{pref_str}")

        # Time line
        open_t, start_t = _parse_start_time(event.start_time)
        if open_t and start_t:
            lines.append(f"{INDENT}🕐 OPEN {open_t} ／ START {start_t}")
        elif start_t:
            lines.append(f"{INDENT}🕐 START {start_t}")
        elif open_t:
            lines.append(f"{INDENT}🕐 OPEN {open_t}")
        # else: no time line

        # Other artists line
        if event.other_artists:
            lines.append(f"{INDENT}👥 {event.other_artists}")

        # Ticket line
        if event.ticket_url:
            site_name = _ticket_site_name(event.ticket_url)
            suppressed_url = f"<{event.ticket_url}>"
            ticket_line = f"{INDENT}🎫 {site_name}  {suppressed_url}"
            if event.ticket_price:
                price = event.ticket_price.lstrip("¥").lstrip("￥").strip()
                ticket_line += f"  💴 ¥{price}"
            lines.append(ticket_line)
        else:
            lines.append(f"{INDENT}🎫 チケット情報未確定")

        return "\n".join(lines)

    def _format_footer(
        self,
        new_count: int,
        updated_count: int,
        today: date,
    ) -> str:
        """サマリーフッター行を生成する。

        フォーマット:
        ``━━━━━━━━━━━━━━━━━━━━━━━━━━━━━``
        ``🆕 新規 N件　✏️ 更新 N件　📆 YYYY/MM/DD 時点``

        Args:
            new_count: 新規イベント件数。
            updated_count: 更新イベント件数。
            today: 集計基準日。

        Returns:
            フッターのテキスト文字列。
        """
        date_str = f"{today.year}/{today.month:02d}/{today.day:02d}"
        return (
            f"{_SEPARATOR_HEAVY}\n"
            f"🆕 新規 {new_count}件　✏️ 更新 {updated_count}件　📆 {date_str} 時点"
        )

    def _post(self, content: str) -> None:
        """Discord Webhook にプレーンテキストで POST する。

        Args:
            content: 送信するテキストコンテンツ。
        """
        if not self.webhook_url:
            logger.warning(
                "DISCORD_WEBHOOK_URL が未設定のため週次サマリー送信をスキップします"
            )
            return
        try:
            response = requests.post(
                self.webhook_url,
                json={"content": content},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("週次サマリー送信に失敗しました: %s", exc)
