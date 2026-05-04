from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class FetchConfig:
    dynamic: bool = False


@dataclass
class NavigationConfig:
    type: str = "single_page"
    # query_param
    param: str = ""
    value_format: str = ""
    granularity: str = "monthly"
    # path_segment
    pattern: str = ""
    # api_endpoint
    endpoint: str = ""
    method: str = "GET"
    body_template: dict[str, Any] = field(default_factory=dict)
    # common
    range_months: int = 3


@dataclass
class ResponseConfig:
    format: str = "json_array"
    array_path: str = ""
    mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class DetailConfig:
    enabled: bool = False
    url_pattern: str = ""
    selectors: dict[str, str] = field(default_factory=dict)


@dataclass
class ArtistConfig:
    name: str
    base_url: str
    analyzed_at: str | None = None
    fetch: FetchConfig = field(default_factory=FetchConfig)
    navigation: NavigationConfig = field(default_factory=NavigationConfig)
    response: ResponseConfig = field(default_factory=ResponseConfig)
    detail: DetailConfig = field(default_factory=DetailConfig)
    selectors: dict[str, str] = field(default_factory=dict)

    @property
    def base_url_origin(self) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(self.base_url)
        return f"{parsed.scheme}://{parsed.netloc}"


@dataclass
class EnvConfig:
    notion_token: str
    notion_database_id: str
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    discord_webhook_url: str = ""
    ai_provider: str = "auto"


@dataclass
class AppConfig:
    artists: list[ArtistConfig]
    env: EnvConfig


def _parse_artist(raw: dict[str, Any]) -> ArtistConfig:
    fetch_raw = raw.get("fetch", {})
    nav_raw = raw.get("navigation", {})
    resp_raw = raw.get("response", {})
    detail_raw = raw.get("detail", {})

    return ArtistConfig(
        name=raw["name"],
        base_url=raw["base_url"],
        analyzed_at=raw.get("analyzed_at"),
        fetch=FetchConfig(dynamic=fetch_raw.get("dynamic", False)),
        navigation=NavigationConfig(
            type=nav_raw.get("type", "single_page"),
            param=nav_raw.get("param", ""),
            value_format=nav_raw.get("value_format", ""),
            granularity=nav_raw.get("granularity", "monthly"),
            pattern=nav_raw.get("pattern", ""),
            endpoint=nav_raw.get("endpoint", ""),
            method=nav_raw.get("method", "GET"),
            body_template=nav_raw.get("body_template", {}),
            range_months=nav_raw.get("range_months", 3),
        ),
        response=ResponseConfig(
            format=resp_raw.get("format", "json_array"),
            array_path=resp_raw.get("array_path", ""),
            mapping=resp_raw.get("mapping", {}),
        ),
        detail=DetailConfig(
            enabled=detail_raw.get("enabled", False),
            url_pattern=detail_raw.get("url_pattern", ""),
            selectors=detail_raw.get("selectors", {}),
        ),
        selectors=raw.get("selectors", {}),
    )


def load_config(
    yaml_path: Path | None = None,
    env_path: Path | None = None,
) -> AppConfig:
    """artists.yaml + .env を読み込んで AppConfig を返す"""
    load_dotenv(env_path or _PROJECT_ROOT / ".env")

    yaml_file = yaml_path or _PROJECT_ROOT / "config" / "artists.yaml"
    with yaml_file.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    artists = [_parse_artist(a) for a in (data.get("artists") or [])]

    env = EnvConfig(
        notion_token=os.environ.get("NOTION_TOKEN", ""),
        notion_database_id=os.environ.get("NOTION_DATABASE_ID", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL", ""),
        ai_provider=os.environ.get("AI_PROVIDER", "auto"),
    )

    return AppConfig(artists=artists, env=env)
