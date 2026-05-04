"""汎用スクレイパー — CSS セレクタ設定ドリブンで HTML をスクレイピングする。(参照: docs/basic-design.md § 4-2. GenericScraper)"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from src.config import ArtistConfig
from src.models.event import LiveEvent
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Date formats to try when parsing Japanese/ISO date strings
_DATE_FORMATS = [
    "%Y年%m月%d日",
    "%Y/%m/%d",
    "%Y-%m-%d",
]


def _parse_date(raw: str) -> date | None:
    """Try each known date format; return None if all fail."""
    text = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    logger.debug("date parse failed for %r", text)
    return None


class GenericScraper(BaseScraper):
    """設定ドリブンの汎用 HTML スクレイパー。

    ``ArtistConfig.selectors`` の CSS セレクタを使ってイベントを抽出する。
    現在は ``navigation.type == 'single_page'`` のみをサポートする。
    """

    def scrape(self, config: ArtistConfig) -> list[LiveEvent]:
        """Scrape live events using the CSS selectors in ArtistConfig.

        Args:
            config: 対象アーティストの設定。``navigation.type`` が
                ``single_page`` 以外の場合は NotImplementedError を送出する。

        Returns:
            抽出した LiveEvent リスト。取得失敗時は空リスト。

        Raises:
            NotImplementedError: ``navigation.type`` が ``single_page`` 以外のとき。
        """
        nav_type = config.navigation.type
        if nav_type != "single_page":
            raise NotImplementedError(
                f"navigation.type '{nav_type}' is not yet supported. "
                "Only 'single_page' is implemented in this version."
            )

        page = self._fetch_static(config.base_url)
        if page is None:
            return []

        return self._parse_events(page, config)

    def _fetch_static(self, url: str) -> Any | None:
        """Fetch a page using Scrapling's static Fetcher.

        Returns the page object, or None if an error occurs.
        """
        try:
            from scrapling.fetchers import Fetcher

            page = Fetcher().get(url, timeout=30)
            return page
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", url, exc)
            return None

    def _parse_events(self, page: Any, config: ArtistConfig) -> list[LiveEvent]:
        """Extract LiveEvent objects from a fetched page using CSS selectors.

        Expected keys in ``config.selectors``:
        - ``event_list``: selector for the list of event container elements
        - ``title``, ``date``, ``venue``, ``start_time``, ``ticket_url``,
          ``poster_url``, ``other_artists`` (all optional except ``event_list``)

        If a selector finds nothing the field is set to ``""`` (never raises).
        """
        selectors = config.selectors

        event_list_sel = selectors.get("event_list", "")
        if not event_list_sel:
            logger.warning(
                "No 'event_list' selector configured for artist '%s'", config.name
            )
            return []

        containers = page.css(event_list_sel)
        if not containers:
            logger.info(
                "Selector '%s' matched no elements for %s",
                event_list_sel,
                config.base_url,
            )
            return []

        events: list[LiveEvent] = []
        for container in containers:
            event = self._parse_single_event(container, config)
            if event is not None:
                events.append(event)

        return events

    def _get_text(self, container: Any, selector: str) -> str:
        """Return stripped text of the first match, or '' if nothing matched."""
        if not selector:
            return ""
        try:
            elements = container.css(selector)
            if elements:
                return (elements[0].text or "").strip()
        except Exception as exc:
            logger.debug("CSS selector %r raised: %s", selector, exc)
        return ""

    def _get_attr(self, container: Any, selector: str, attr: str) -> str:
        """Return the named attribute of the first match, or ''."""
        if not selector:
            return ""
        try:
            elements = container.css(selector)
            if elements:
                value = elements[0].attrib.get(attr, "")
                return (value or "").strip()
        except Exception as exc:
            logger.debug("CSS selector %r attr %r raised: %s", selector, attr, exc)
        return ""

    def _resolve_field(self, container: Any, selectors: dict[str, str], key: str) -> str:
        """Resolve a field value from a selector.

        Supports ``::attr(name)`` pseudo-element suffix for attribute extraction,
        otherwise returns text content.
        """
        selector = selectors.get(key, "")
        if not selector:
            return ""

        if "::attr(" in selector:
            # e.g. "a.ticket::attr(href)"
            attr_start = selector.index("::attr(")
            css_part = selector[:attr_start]
            attr_name = selector[attr_start + 7:].rstrip(")")
            return self._get_attr(container, css_part, attr_name)

        return self._get_text(container, selector)

    def _parse_single_event(
        self, container: Any, config: ArtistConfig
    ) -> LiveEvent | None:
        """Parse one event container element into a LiveEvent."""
        selectors = config.selectors

        title = self._resolve_field(container, selectors, "title")
        date_raw = self._resolve_field(container, selectors, "date")
        parsed_date = _parse_date(date_raw) if date_raw else None

        # title is required; skip container if absent
        if not title:
            logger.debug("Skipping container with empty title under '%s'", config.name)
            return None

        return LiveEvent(
            title=title,
            artist=config.name,
            date=parsed_date,
            start_time=self._resolve_field(container, selectors, "start_time"),
            venue=self._resolve_field(container, selectors, "venue"),
            prefecture=self._resolve_field(container, selectors, "prefecture"),
            ticket_url=self._resolve_field(container, selectors, "ticket_url"),
            ticket_price=self._resolve_field(container, selectors, "ticket_price"),
            other_artists=self._resolve_field(container, selectors, "other_artists"),
            poster_url=self._resolve_field(container, selectors, "poster_url"),
            source_url=config.base_url,
        )
