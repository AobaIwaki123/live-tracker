"""汎用スクレイパー — CSS セレクタ設定ドリブンで HTML をスクレイピングする。(参照: docs/basic-design.md § 4-2. GenericScraper)"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin

from dateutil.relativedelta import relativedelta

from src.config import ArtistConfig, DetailConfig
from src.models.event import LiveEvent
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

_DATE_FORMATS = [
    "%Y年%m月%d日",
    "%Y/%m/%d",
    "%Y-%m-%d",
]


def _parse_date(raw: str) -> date | None:
    """Try each known date format or Unix timestamp; return None if all fail."""
    text = raw.strip()
    if not text:
        return None

    # Try Unix timestamp (seconds or milliseconds)
    if text.isdigit():
        val = int(text)
        try:
            # If > 10^12, assume milliseconds
            if val > 1000000000000:
                return datetime.fromtimestamp(val / 1000).date()
            return datetime.fromtimestamp(val).date()
        except (ValueError, OSError):
            pass

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    logger.debug("date parse failed for %r", text)
    return None


def _deep_get(data: Any, path: str, default: str = "") -> Any:
    """ドット区切りパスでネストした辞書から値を取得する。

    Args:
        data: 対象辞書。
        path: ドット区切りのキーパス（例: ``"title.content"``）。空文字は ``default`` を返す。
        default: キーが存在しない場合の返り値。

    Returns:
        パスが示す値。途中でキーが見つからない場合は ``default``。
    """
    if not path:
        return default
    for key in path.split("."):
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
        if data is default:
            return default
    return data


class GenericScraper(BaseScraper):
    """設定ドリブンの汎用スクレイパー。

    ``navigation.type`` に応じて HTML スクレイピングまたは API 呼び出しを行う。
    現在サポートするタイプ: ``single_page``, ``api_endpoint``。
    """

    def scrape(self, config: ArtistConfig) -> list[LiveEvent]:
        """Scrape live events using the ArtistConfig.

        Args:
            config: 対象アーティストの設定。

        Returns:
            抽出した LiveEvent リスト。取得失敗時は空リスト。

        Raises:
            NotImplementedError: ``navigation.type`` が未実装のとき。
        """
        nav_type = config.navigation.type

        if nav_type == "api_endpoint":
            events = self._scrape_api(config)
        elif nav_type == "single_page":
            page = self._fetch_page(config.base_url, config.fetch.dynamic)
            events = [] if page is None else self._parse_events(page, config)
        elif nav_type == "pagination_links":
            events = self._scrape_pagination_links(config)
        else:
            raise NotImplementedError(
                f"navigation.type '{nav_type}' is not yet supported. "
                "Supported types: 'single_page', 'api_endpoint', 'pagination_links'."
            )

        today = date.today()
        cutoff = today + relativedelta(months=config.navigation.range_months)
        return [e for e in events if e.date and today <= e.date <= cutoff]

    def _scrape_pagination_links(self, config: ArtistConfig) -> list[LiveEvent]:
        """pagination_links タイプのスクレイピングを実行する。

        ``config.selectors["next_page"]`` を次ページリンクのセレクタとして使う。
        上限ページ数は ``config.navigation.range_months * 10``。

        Args:
            config: 対象アーティストの設定。

        Returns:
            全ページから収集した重複除去済み LiveEvent リスト。
        """
        next_selector = config.selectors.get("next_page", "")
        if not next_selector:
            logger.warning(
                "Artist '%s': navigation.type is 'pagination_links' but "
                "'next_page' key is missing from selectors. "
                "Falling back to single-page scrape.",
                config.name,
            )
            page = self._fetch_page(config.base_url, config.fetch.dynamic)
            if page is None:
                return []
            return self._parse_events(page, config)

        max_pages = config.navigation.range_months * 10
        return self._follow_next_links(config.base_url, next_selector, max_pages, config)

    def _follow_next_links(
        self,
        start_url: str,
        next_selector: str,
        max_pages: int,
        config: ArtistConfig,
    ) -> list[LiveEvent]:
        """次ページリンクを辿り全ページのイベントを収集する。

        相対 URL は ``urllib.parse.urljoin`` で絶対 URL に変換する。
        ``identity_key`` による重複除去を行うため、同一ページが複数回取得されても安全。

        Args:
            start_url: 最初のページの URL。
            next_selector: 次ページリンクの CSS セレクタ（``::attr(href)`` なし）。
            max_pages: 最大取得ページ数。この数を超えたら警告を出して打ち切る。
            config: 対象アーティストの設定。

        Returns:
            全ページから収集した重複除去済み LiveEvent リスト。
        """
        events: list[LiveEvent] = []
        seen: set[tuple[str, str, date | None]] = set()
        url = start_url
        pages_fetched = 0

        for _ in range(max_pages):
            page = self._fetch_page(url, config.fetch.dynamic)
            if page is None:
                break

            pages_fetched += 1

            for event in self._parse_events(page, config):
                key = event.identity_key()
                if key not in seen:
                    seen.add(key)
                    events.append(event)

            raw_next = page.css(next_selector + "::attr(href)").get()
            if not raw_next:
                break

            url = urljoin(url, raw_next)
        else:
            logger.warning(
                "Artist '%s': reached max_pages limit (%d) while following "
                "pagination links. Some pages may not have been scraped.",
                config.name,
                max_pages,
            )

        logger.info(
            "Artist '%s': collected %d unique events across %d page(s).",
            config.name,
            len(events),
            pages_fetched,
        )
        return events

    def _scrape_api(self, config: ArtistConfig) -> list[LiveEvent]:
        """api_endpoint タイプのスクレイピングを実行する。

        Args:
            config: 対象アーティストの設定。

        Returns:
            全ターゲット分の LiveEvent リスト。
        """
        from dataclasses import replace as dc_replace

        from src.scrapers.url_generator import generate_targets

        # {version_dir} プレースホルダーが設定されている場合、base_url を取得して解決する
        resolved_config = config
        if "{version_dir}" in config.navigation.endpoint and config.navigation.version_dir_regex:
            version_dir = self._extract_version_dir(config.base_url, config.navigation.version_dir_regex)
            if version_dir:
                new_nav = dc_replace(
                    config.navigation,
                    endpoint=config.navigation.endpoint.replace("{version_dir}", version_dir),
                )
                resolved_config = dc_replace(config, navigation=new_nav)
            else:
                logger.warning(
                    "Artist '%s': could not extract version_dir from %s",
                    config.name,
                    config.base_url,
                )

        targets = generate_targets(resolved_config)
        all_events: list[LiveEvent] = []
        seen: set[tuple[str, str, date | None]] = set()

        for target in targets:
            raw_list = self._call_api(target, resolved_config.response.array_path)
            raw_list = self._filter_raw_items(raw_list, resolved_config)
            events = self._map_api_response(
                raw_list, resolved_config.response.mapping, resolved_config.name,
                resolved_config.base_url_origin,
            )
            for event in events:
                if resolved_config.detail.enabled:
                    event = self._fetch_detail(
                        event, resolved_config.detail, resolved_config.base_url
                    )

                key = event.identity_key()
                if key not in seen:
                    seen.add(key)
                    all_events.append(event)
        return all_events

    def _extract_version_dir(self, url: str, pattern: str) -> str | None:
        """ページ HTML から正規表現でバージョンディレクトリ文字列を抽出する。

        Args:
            url: 取得先 URL（アーティストの base_url）。
            pattern: バージョン文字列を抽出する正規表現。グループ 1 を使用。

        Returns:
            抽出したバージョン文字列。失敗時は None。
        """
        import re

        import httpx

        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30,
                follow_redirects=True,
            )
            resp.raise_for_status()
            match = re.search(pattern, resp.text)
            if match:
                return match.group(1)
            logger.warning("version_dir_regex %r matched nothing in %s", pattern, url)
            return None
        except Exception as exc:
            logger.error("Failed to extract version_dir from %s: %s", url, exc)
            return None

    def _filter_raw_items(self, items: list[dict], config: ArtistConfig) -> list[dict]:
        """navigation 設定のフィルタ条件に従い生 JSON アイテムを絞り込む。

        Args:
            items: API レスポンスの JSON 配列。
            config: アーティスト設定。

        Returns:
            絞り込み後のアイテムリスト。
        """
        nav = config.navigation
        if nav.filter_category:
            items = [i for i in items if i.get("category") == nav.filter_category]
        if nav.filter_artist_ids:
            id_set = set(nav.filter_artist_ids)
            items = [i for i in items if id_set.intersection(i.get("artistsSearch", []))]
        return items

    def _call_api(self, target: Any, array_path: str = "") -> list[dict]:
        """HTTP リクエストを送信し JSON 配列を返す。

        Args:
            target: ScrapeTarget。``target.api`` が設定されている前提。
            array_path: ルートが配列でない場合の配列へのパス（ドット区切り）。

        Returns:
            JSON 配列。取得失敗時は空リスト。
        """
        import httpx

        if target.api is None:
            return []

        api = target.api
        try:
            if api.method.upper() == "POST":
                resp = httpx.post(api.url, json=api.body, headers=api.headers, timeout=30)
            else:
                resp = httpx.get(api.url, params=api.body, headers=api.headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if array_path:
                for key in array_path.split("."):
                    data = data[key]
            if isinstance(data, list):
                return data
            logger.warning("API response is not a list for %s", api.url)
            return []
        except Exception as exc:
            logger.error("API request failed for %s: %s", api.url, exc)
            return []

    def _map_api_response(
        self, raw: list[dict], mapping: dict[str, str], artist: str,
        base_url_origin: str = "",
    ) -> list[LiveEvent]:
        """response.mapping 設定に従い dict → LiveEvent 変換する。

        ``mapping`` の構造: LiveEvent フィールド名 → JSON キー名。
        キー名に ``::regex(pattern)`` サフィックスを付けることで正規表現抽出が可能。
        ``date_format`` は特別キーとして日付パースフォーマットに使用する。
        ``source_url`` が相対パス（``/`` 始まり）の場合、``base_url_origin`` を自動付与する。

        Args:
            raw: API レスポンスの JSON 配列。
            mapping: LiveEvent フィールド名 → JSON キー名の辞書。
            artist: アーティスト識別子。
            base_url_origin: 相対 source_url に付与するオリジン（例: ``https://example.com``）。

        Returns:
            変換後の LiveEvent リスト。変換失敗した要素はスキップ。
        """
        import re

        date_fmt = mapping.get("date_format", "")
        events: list[LiveEvent] = []
        for item in raw:
            try:

                def _resolve(key_path: str) -> str:
                    if not key_path:
                        return ""
                    if "::regex(" in key_path:
                        path, pattern = key_path.split("::regex(", 1)
                        if pattern.endswith(")"):
                            pattern = pattern[:-1]
                        val = str(_deep_get(item, path) or "")
                        m = re.search(pattern, val)
                        if m:
                            return (
                                m.group(1).strip()
                                if m.lastindex
                                else m.group(0).strip()
                            )
                        return ""
                    return str(_deep_get(item, key_path) or "").strip()

                title = _resolve(mapping.get("title", "title"))
                if not title:
                    logger.debug("Skipping item with empty title")
                    continue

                date_raw = _resolve(mapping.get("date", "date"))
                if date_fmt:
                    try:
                        parsed_date = datetime.strptime(date_raw, date_fmt).date()
                    except ValueError:
                        parsed_date = _parse_date(date_raw)
                else:
                    parsed_date = _parse_date(date_raw)

                event_id = _resolve(mapping.get("id", "id"))
                venue = _resolve(mapping.get("venue", ""))
                start_time = _resolve(mapping.get("start_time", ""))
                ticket_url = _resolve(mapping.get("ticket_url", ""))
                source_url = _resolve(mapping.get("source_url", ""))
                if source_url.startswith("/") and base_url_origin:
                    source_url = base_url_origin + source_url
                other_artists = _resolve(mapping.get("other_artists", ""))
                poster_url = _resolve(mapping.get("poster_url", ""))

                events.append(
                    LiveEvent(
                        title=title,
                        artist=artist,
                        date=parsed_date,
                        id=event_id,
                        venue=venue,
                        start_time=start_time,
                        ticket_url=ticket_url,
                        source_url=source_url,
                        other_artists=other_artists,
                        poster_url=poster_url,
                    )
                )
            except Exception as exc:
                logger.debug("Skipping item due to mapping error: %s", exc)
        return events

    def _fetch_detail(
        self, event: LiveEvent, detail_config: DetailConfig, base_url: str
    ) -> LiveEvent:
        """詳細ページへアクセスし追加フィールドを補完する。

        Args:
            event: 補完対象の LiveEvent。
            detail_config: 詳細ページ取得設定。
            base_url: アーティスト設定の base_url。URL パターン展開に使用。

        Returns:
            フィールド補完後の LiveEvent。取得失敗時は元の event をそのまま返す。
        """
        if not event.id:
            return event

        date_str = event.date.strftime("%Y-%m-%d") if event.date else ""
        url = (
            detail_config.url_pattern
            .replace("{base_url}", base_url)
            .replace("{id}", event.id)
            .replace("{date}", date_str)
        )

        page = self._fetch_static(url)
        if page is None:
            return event

        selectors = detail_config.selectors
        venue = self._resolve_field(page, selectors, "venue") or event.venue
        start_time = self._resolve_field(page, selectors, "start_time") or event.start_time
        ticket_url = self._resolve_field(page, selectors, "ticket_url") or event.ticket_url
        other_artists = self._resolve_field(page, selectors, "other_artists") or event.other_artists
        poster_url = self._resolve_field(page, selectors, "poster_url") or event.poster_url

        from dataclasses import replace
        return replace(
            event,
            venue=venue,
            start_time=start_time,
            ticket_url=ticket_url,
            other_artists=other_artists,
            poster_url=poster_url,
            source_url=url,
        )

    def _fetch_page(self, url: str, dynamic: bool) -> Any | None:
        """static または dynamic フェッチャーでページを取得する。

        Args:
            url: 取得対象 URL。
            dynamic: True のとき Playwright ベースの DynamicFetcher を使用する。

        Returns:
            ``.css()`` セレクタ呼び出し可能な Page オブジェクト、またはエラー時 None。
        """
        if dynamic:
            try:
                from scrapling.fetchers import DynamicFetcher

                page = DynamicFetcher().fetch(url, timeout=30000)
                return page
            except Exception as exc:
                logger.error("DynamicFetcher failed for %s: %s", url, exc)
                return None
        return self._fetch_static(url)

    def _fetch_static(self, url: str) -> Any | None:
        """Fetch a page using Scrapling's static Fetcher.

        Args:
            url: 取得対象 URL。

        Returns:
            Page オブジェクト、またはエラー時 None。
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

        Args:
            page: Scrapling の Page オブジェクト。
            config: 対象アーティストの設定。

        Returns:
            抽出した LiveEvent リスト。
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
        """Return stripped text of the first match, or '' if nothing matched.

        Uses ``get_all_text()`` to capture text across nested child elements
        (e.g. content separated by ``<br>`` or wrapped in ``<b>``).
        """
        if not selector:
            return ""
        try:
            elements = container.css(selector)
            if elements:
                return elements[0].get_all_text(separator="\n").strip()
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

        Supports three pseudo-element suffixes:
        - ``::attr(name)`` — extract the named HTML attribute.
        - ``::regex(pattern)`` — apply a regex to the text; returns group(1) if present.
        - (none) — return the text content.

        Args:
            container: Scrapling の要素またはページオブジェクト。
            selectors: CSS セレクタ辞書。
            key: 取得するフィールド名。

        Returns:
            抽出したフィールド値。セレクタ未設定や未マッチの場合は空文字。
        """
        import re

        selector = selectors.get(key, "")
        if not selector:
            return ""

        if "::attr(" in selector:
            attr_start = selector.index("::attr(")
            css_part = selector[:attr_start]
            attr_name = selector[attr_start + 7:].rstrip(")")
            return self._get_attr(container, css_part, attr_name)

        if "::regex(" in selector:
            regex_start = selector.index("::regex(")
            css_part = selector[:regex_start]
            pattern = selector[regex_start + 8:-1]  # strip only the final closing )
            elements = container.css(css_part) if css_part else [container]
            for el in elements:
                text = el.get_all_text(separator="\n").strip()
                m = re.search(pattern, text)
                if m:
                    return m.group(1).strip() if m.lastindex else m.group(0).strip()
            return ""

        return self._get_text(container, selector)

    def _parse_single_event(
        self, container: Any, config: ArtistConfig
    ) -> LiveEvent | None:
        """Parse one event container element into a LiveEvent.

        Args:
            container: 1 イベント分の要素コンテナ。
            config: 対象アーティストの設定。

        Returns:
            LiveEvent、またはタイトルが取得できない場合は None。
        """
        selectors = config.selectors

        title = self._resolve_field(container, selectors, "title")
        date_raw = self._resolve_field(container, selectors, "date")
        parsed_date = _parse_date(date_raw) if date_raw else None

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
