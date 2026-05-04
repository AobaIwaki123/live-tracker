"""AI エンリッチメント — 欠損フィールドをチケットサイト検索で補完する（opt-in）。(参照: docs/requirements.md § FR-06)"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any
from urllib.parse import quote_plus

from src.ai.provider import AIProvider, get_ai_provider
from src.models.event import LiveEvent
from src.notion.client import NotionClient, NotionRecord

logger = logging.getLogger(__name__)

TICKET_SITES = [
    "site:eplus.jp",
    "site:t.pia.jp",
    "site:l-tike.com",
]

_ENRICHABLE_FIELDS = ("venue", "prefecture", "ticket_price", "ticket_url", "other_artists")

_SYSTEM_PROMPT = """\
あなたはアイドルライブイベント情報の抽出アシスタントです。
HTML テキストからイベントの以下フィールドを抽出してください。

出力は必ず以下の JSON のみで返してください（説明文不要）:
{"venue": "会場名", "prefecture": "都道府県名", "ticket_price": "料金", "ticket_url": "チケットURL", "other_artists": "出演アーティスト"}

確認できない項目は空文字にしてください。推測による誤情報は絶対に含めないでください。
"""


def _build_prompt(event: LiveEvent, html: str) -> str:
    info = (
        f"グループ名: {event.artist}\n"
        f"公演タイトル: {event.title}\n"
        f"開催日: {event.date.isoformat() if event.date else '不明'}\n\n"
        f"--- 検索結果 HTML ---\n{html[:4000]}"
    )
    return info


def _parse_response(response: str) -> dict[str, Any]:
    try:
        text = response.strip()
        if "```" in text:
            lines = [l for l in text.splitlines() if not l.startswith("```")]
            text = "\n".join(lines)
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        logger.debug("AI レスポンスのパースに失敗しました: %r", response[:200])
        return {}


def _is_relevant(extracted: dict[str, Any], event: LiveEvent) -> bool:
    """Return False when the AI result has no plausible connection to the event."""
    if not extracted:
        return False
    # 少なくとも 1 フィールドが非空であることを確認
    return any(v for v in extracted.values() if v)


def _compute_diff(event: LiveEvent, enriched: dict[str, Any]) -> dict[str, Any]:
    """Return non-empty enriched values only for currently blank fields."""
    diff: dict[str, Any] = {}
    for field_name in _ENRICHABLE_FIELDS:
        current = getattr(event, field_name, "")
        new_value = enriched.get(field_name, "")
        if new_value and not current:
            diff[field_name] = new_value
    return diff


def _record_to_event(record: NotionRecord) -> LiveEvent:
    fields = record.fields
    raw_date = fields.get("date")
    parsed_date: date | None = raw_date if isinstance(raw_date, date) else None
    return LiveEvent(
        title=fields.get("title", ""),
        artist=fields.get("artist", ""),
        date=parsed_date,
        start_time=fields.get("start_time", ""),
        venue=fields.get("venue", ""),
        prefecture=fields.get("prefecture", ""),
        ticket_url=fields.get("ticket_url", ""),
        ticket_price=fields.get("ticket_price", ""),
        other_artists=fields.get("other_artists", ""),
        poster_url=fields.get("poster_url", ""),
        source_url=fields.get("source_url", ""),
    )


class Enricher:
    """Notion DB の欠損フィールドを AI で補完するエンリッチャー。

    ``取得ステータス`` が ``詳細取得済み`` 以外のレコードを対象に、
    チケットサイトの Google 検索結果 HTML を AI に渡してフィールドを抽出し、
    Notion の空欄フィールドのみを上書き更新する（FR-06）。

    Raises:
        EnvironmentError: NotionClient または AIProvider の初期化に失敗した場合。
    """

    def __init__(
        self,
        notion_client: NotionClient | None = None,
        ai_provider: AIProvider | None = None,
    ) -> None:
        self._notion = notion_client or NotionClient()
        self._ai = ai_provider or get_ai_provider()

    def enrich(self, event: LiveEvent) -> dict[str, str]:
        """空欄フィールドをチケットサイト検索で補完して差分辞書を返す。

        Args:
            event: 補完対象のライブイベント。

        Returns:
            補完できたフィールドのみを含む ``{field_name: value}`` 辞書。
            補完不要・失敗時は空辞書。
        """
        query = quote_plus(f"{event.title} {event.artist} {event.date}")
        for site in TICKET_SITES:
            try:
                from scrapling.fetchers import Fetcher
                page = Fetcher().get(
                    f"https://www.google.com/search?q={query}+{site}",
                    timeout=15,
                )
                html = page.html if hasattr(page, "html") else str(page)
            except Exception as exc:
                logger.debug("Google 検索の取得に失敗しました (site=%s): %s", site, exc)
                continue

            extracted = self._extract_fields(html, event)
            if extracted:
                return extracted

        return {}

    def _extract_fields(self, html: str, event: LiveEvent) -> dict[str, str]:
        prompt = _build_prompt(event, html)
        try:
            response = self._ai.complete(_SYSTEM_PROMPT, prompt)
        except Exception as exc:
            logger.warning(
                "AI 呼び出しに失敗しました (artist=%s, title=%s): %s",
                event.artist,
                event.title,
                exc,
            )
            return {}

        raw = _parse_response(response)
        if not _is_relevant(raw, event):
            return {}
        return _compute_diff(event, raw)

    def enrich_all(
        self,
        records: list[LiveEvent],
    ) -> list[tuple[LiveEvent, dict]]:
        """全対象レコードを enrich して Notion 更新し、更新リストを返す。

        Args:
            records: 補完対象のライブイベントリスト。

        Returns:
            更新した ``[(event, diff), ...]`` のリスト。
        """
        results: list[tuple[LiveEvent, dict]] = []
        for event in records:
            diff = self.enrich(event)
            if not diff:
                continue
            logger.info(
                "補完: artist=%s, title=%s, fields=%s",
                event.artist,
                event.title,
                list(diff.keys()),
            )
            results.append((event, diff))
        return results

    def run(self, artist_filter: str | None = None) -> None:
        """Notion DB から補完対象レコードを取得してエンリッチメントを実行する。

        Args:
            artist_filter: 指定したアーティスト名のみを処理する。None のとき全件対象。
        """
        logger.info("エンリッチメント開始 (artist=%s)", artist_filter or "全件")
        all_records = self._notion.fetch_all()

        targets = [
            (key, record)
            for key, record in all_records.items()
            if record.fields.get("fetch_status") != "詳細取得済み"
            and (artist_filter is None or record.fields.get("artist") == artist_filter)
        ]
        logger.info("補完対象: %d 件", len(targets))

        updated_count = 0
        for _key, record in targets:
            event = _record_to_event(record)
            diff = self.enrich(event)
            if not diff:
                continue

            # fetch_status を補完後の値で再計算
            patched = LiveEvent(
                title=event.title,
                artist=event.artist,
                date=event.date,
                start_time=event.start_time,
                venue=diff.get("venue", event.venue),
                prefecture=diff.get("prefecture", event.prefecture),
                ticket_url=diff.get("ticket_url", event.ticket_url),
                ticket_price=diff.get("ticket_price", event.ticket_price),
                other_artists=diff.get("other_artists", event.other_artists),
                poster_url=event.poster_url,
                source_url=event.source_url,
            )
            diff["fetch_status"] = patched.fetch_status

            self._notion.update(record.page_id, diff)
            updated_count += 1
            logger.info(
                "更新完了: artist=%s, title=%s → %s",
                event.artist,
                event.title,
                patched.fetch_status,
            )

        logger.info("エンリッチメント完了: %d 件更新", updated_count)
