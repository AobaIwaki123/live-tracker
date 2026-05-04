from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from src.models.event import LiveEvent

logger = logging.getLogger(__name__)

# Maps LiveEvent field names to (Notion property name, Notion property type)
FIELD_MAP: dict[str, tuple[str, str]] = {
    "title":         ("イベントタイトル", "title"),
    "artist":        ("グループ名",        "select"),
    "date":          ("開催日",            "date"),
    "start_time":    ("開始時刻",          "rich_text"),
    "venue":         ("会場名",            "rich_text"),
    "prefecture":    ("都道府県",          "select"),
    "ticket_url":    ("チケット URL",      "url"),
    "ticket_price":  ("チケット料金",      "rich_text"),
    "other_artists": ("出演アーティスト",  "rich_text"),
    "poster_url":    ("ポスター画像 URL",  "url"),
    "source_url":    ("ソース URL",        "url"),
    "fetch_status":  ("取得ステータス",    "select"),
}


@dataclass
class NotionRecord:
    """Holds a Notion page_id and a flat dict of field values for comparison."""

    page_id: str
    fields: dict[str, Any]  # field name -> python value (str, date, None)


def _build_property(notion_type: str, value: Any) -> dict[str, Any]:
    """Build a single Notion property payload from a python value."""
    if notion_type == "title":
        return {"title": [{"text": {"content": str(value) if value else ""}}]}
    elif notion_type == "rich_text":
        return {"rich_text": [{"text": {"content": str(value) if value else ""}}]}
    elif notion_type == "select":
        if value:
            return {"select": {"name": str(value)}}
        else:
            return {"select": None}
    elif notion_type == "date":
        if value is None:
            return {"date": None}
        if isinstance(value, date):
            return {"date": {"start": value.isoformat()}}
        # Already a string
        return {"date": {"start": str(value)}}
    elif notion_type == "url":
        if value:
            return {"url": str(value)}
        else:
            return {"url": None}
    else:
        raise ValueError(f"Unknown Notion property type: {notion_type}")


def _build_properties(event: LiveEvent) -> dict[str, Any]:
    """Build a full Notion properties payload from a LiveEvent."""
    props: dict[str, Any] = {}
    for field_name, (notion_name, notion_type) in FIELD_MAP.items():
        value = getattr(event, field_name)
        props[notion_name] = _build_property(notion_type, value)
    return props


def _build_properties_from_diff(diff: dict[str, Any]) -> dict[str, Any]:
    """Build a partial Notion properties payload from a diff dict {field_name: value}."""
    props: dict[str, Any] = {}
    for field_name, value in diff.items():
        if field_name not in FIELD_MAP:
            continue
        notion_name, notion_type = FIELD_MAP[field_name]
        props[notion_name] = _build_property(notion_type, value)
    return props


def _extract_field_value(notion_type: str, prop: dict[str, Any]) -> Any:
    """Extract a python value from a Notion property dict."""
    try:
        if notion_type == "title":
            items = prop.get("title", [])
            return items[0]["text"]["content"] if items else ""
        elif notion_type == "rich_text":
            items = prop.get("rich_text", [])
            return items[0]["text"]["content"] if items else ""
        elif notion_type == "select":
            sel = prop.get("select")
            return sel["name"] if sel else ""
        elif notion_type == "date":
            d = prop.get("date")
            if d and d.get("start"):
                try:
                    return date.fromisoformat(d["start"])
                except ValueError:
                    return d["start"]
            return None
        elif notion_type == "url":
            return prop.get("url") or ""
    except (KeyError, IndexError, TypeError):
        return ""
    return ""


def _parse_notion_page(page: dict[str, Any]) -> NotionRecord:
    """Parse a raw Notion page dict into a NotionRecord."""
    page_id = page["id"]
    properties = page.get("properties", {})
    fields: dict[str, Any] = {}
    for field_name, (notion_name, notion_type) in FIELD_MAP.items():
        prop = properties.get(notion_name, {})
        fields[field_name] = _extract_field_value(notion_type, prop)
    return NotionRecord(page_id=page_id, fields=fields)


class NotionClient:
    def __init__(self) -> None:
        token = os.environ.get("NOTION_TOKEN", "")
        db_id = os.environ.get("NOTION_DATABASE_ID", "")
        if not token or not db_id:
            raise EnvironmentError(
                "NOTION_TOKEN と NOTION_DATABASE_ID を .env に設定してください"
            )
        self._client = Client(auth=token)
        self._db_id = db_id

    def fetch_all(self) -> dict[tuple, NotionRecord]:
        """Fetch all DB pages; returns {(artist, title, date): NotionRecord}."""
        result: dict[tuple, NotionRecord] = {}
        cursor: str | None = None

        while True:
            try:
                kwargs: dict[str, Any] = {"database_id": self._db_id, "page_size": 100}
                if cursor:
                    kwargs["start_cursor"] = cursor

                response = self._client.databases.query(**kwargs)
            except APIResponseError as exc:
                logger.error("Notion DB クエリ中にエラーが発生しました: %s", exc)
                break

            for page in response.get("results", []):
                try:
                    record = _parse_notion_page(page)
                    key = (
                        record.fields.get("artist", ""),
                        record.fields.get("title", ""),
                        record.fields.get("date"),
                    )
                    result[key] = record
                except Exception as exc:  # noqa: BLE001
                    logger.error("ページのパース中にエラーが発生しました (page_id=%s): %s", page.get("id"), exc)

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return result

    def create(self, event: LiveEvent) -> str:
        """Create a new Notion page; return page_id."""
        try:
            props = _build_properties(event)
            response = self._client.pages.create(
                parent={"database_id": self._db_id},
                properties=props,
            )
            page_id: str = response["id"]
            logger.info("作成: %s / %s → page_id=%s", event.artist, event.title, page_id)
            return page_id
        except APIResponseError as exc:
            logger.error(
                "ページ作成中にエラーが発生しました (artist=%s, title=%s): %s",
                event.artist,
                event.title,
                exc,
            )
            return ""

    def update(self, page_id: str, diff: dict[str, Any]) -> None:
        """Update only the differing fields on an existing page."""
        try:
            props = _build_properties_from_diff(diff)
            self._client.pages.update(page_id=page_id, properties=props)
            logger.info("更新: page_id=%s, フィールド=%s", page_id, list(diff.keys()))
        except APIResponseError as exc:
            logger.error(
                "ページ更新中にエラーが発生しました (page_id=%s): %s",
                page_id,
                exc,
            )

    def upsert_events(
        self, events: list[LiveEvent]
    ) -> tuple[list[LiveEvent], list[tuple[LiveEvent, dict]]]:
        """
        For each event:
          - if key not in existing → create
          - if key exists and diff → update
          - if key exists and no diff → skip
        Returns (created_events, [(event, diff_fields), ...])
        """
        existing = self.fetch_all()
        created_events: list[LiveEvent] = []
        updated_events: list[tuple[LiveEvent, dict]] = []

        for event in events:
            key = event.identity_key()
            record = existing.get(key)

            if record is None:
                # New event — create
                page_id = self.create(event)
                if page_id:
                    created_events.append(event)
            else:
                # Existing event — compute diff
                diff = _compute_diff(event, record)
                if diff:
                    # Always include recomputed fetch_status when updating
                    diff["fetch_status"] = event.fetch_status
                    self.update(record.page_id, diff)
                    updated_events.append((event, diff))
                else:
                    logger.debug("スキップ: %s / %s (変更なし)", event.artist, event.title)

        return created_events, updated_events


def _compute_diff(event: LiveEvent, record: NotionRecord) -> dict[str, Any]:
    """
    Return a dict of fields where the scraped value differs from the stored value.
    Only includes fields where scraped_field != "" (non-empty scraped values win).
    """
    diff: dict[str, Any] = {}
    for field_name in FIELD_MAP:
        if field_name == "fetch_status":
            # fetch_status is always recomputed from the event; handled separately
            continue
        scraped_value = getattr(event, field_name)
        # Skip empty scraped values — don't overwrite existing data with blanks
        if scraped_value == "" or scraped_value is None:
            continue
        existing_value = record.fields.get(field_name)
        if scraped_value != existing_value:
            diff[field_name] = scraped_value
    return diff
