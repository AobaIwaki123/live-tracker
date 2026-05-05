"""アーティスト設定と環境変数を管理するローダー。(参照: docs/basic-design.md § 2. YAML 設定ファイル設計)"""
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
    """ページ取得方式の設定。

    Attributes:
        dynamic: True のとき Playwright による JS レンダリングが必要。
    """

    dynamic: bool = False


@dataclass
class NavigationConfig:
    """スケジュールページの Navigation 方式設定。

    ``type`` に応じてフィールドの使われ方が変わる。
    詳細は docs/basic-design.md § 3. Navigation タイプ別 URL 生成ロジック を参照。

    Attributes:
        type: navigation タイプ。single_page / query_param / path_segment /
            pagination_links / api_endpoint のいずれか。
        param: query_param タイプ時のクエリパラメータ名。
        value_format: query_param タイプ時の strftime フォーマット。
        granularity: query_param タイプ時の粒度。monthly または weekly。
        pattern: path_segment タイプ時の URL パターン。
        endpoint: api_endpoint タイプ時のエンドポイントパス。
        method: api_endpoint タイプ時の HTTP メソッド。
        body_template: api_endpoint タイプ時のリクエストボディテンプレート。
        range_months: 何ヶ月先まで収集するか（全タイプ共通）。
    """

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
    headers: dict[str, str] = field(default_factory=dict)
    version_dir_regex: str = ""
    filter_artist_ids: list[int] = field(default_factory=list)
    filter_category: str = ""
    # common
    range_months: int = 3


@dataclass
class ResponseConfig:
    """api_endpoint タイプ時のレスポンス解釈設定。

    Attributes:
        format: レスポンス形式。json_array または json_object_with_array。
        array_path: ルートが配列でない場合の配列へのパス。空文字でルートが配列。
        mapping: JSON キーから LiveEvent フィールドへのマッピング。
    """

    format: str = "json_array"
    array_path: str = ""
    mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class DetailConfig:
    """詳細ページからの追加情報取得設定。

    Attributes:
        enabled: 詳細ページ取得を有効にするか。
        url_pattern: 詳細ページ URL のパターン（{base_url}/{id}?d={date} 形式）。
        selectors: 詳細ページの CSS セレクタ。venue / start_time / ticket_url 等。
    """

    enabled: bool = False
    url_pattern: str = ""
    selectors: dict[str, str] = field(default_factory=dict)


@dataclass
class ArtistConfig:
    """アーティスト 1 件分の設定。YAML の 1 エントリに対応。

    Attributes:
        name: アーティスト識別子。
        base_url: スケジュールページのルート URL。ユーザーが唯一指定する入力。
        analyzed_at: analyze コマンドが記録した解析日（YYYY-MM-DD）。None なら未解析。
        fetch: ページ取得方式設定。
        navigation: Navigation 方式設定。
        response: api_endpoint タイプ時のレスポンス解釈設定。
        detail: 詳細ページ取得設定。
        selectors: HTML スクレイピング型の CSS セレクタ辞書。
    """

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
        """Return scheme + host of base_url (e.g. ``https://example.com``)."""
        from urllib.parse import urlparse
        parsed = urlparse(self.base_url)
        return f"{parsed.scheme}://{parsed.netloc}"


@dataclass
class EnvConfig:
    """環境変数から読み込む認証情報・設定値。

    Attributes:
        notion_token: Notion Integration Token。
        notion_database_id: 書き込み先 Notion データベース ID。
        anthropic_api_key: Claude API キー。
        gemini_api_key: Gemini API キー。
        discord_webhook_url: Discord Webhook URL。未設定時は通知をスキップ。
        ai_provider: AI プロバイダー選択。auto / claude / gemini。
    """

    notion_token: str
    notion_database_id: str
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    discord_webhook_url: str = ""
    ai_provider: str = "auto"


@dataclass
class AppConfig:
    """アプリケーション全体の設定。

    Attributes:
        artists: アーティスト設定リスト。
        env: 環境変数設定。
    """

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
            headers=nav_raw.get("headers", {}),
            version_dir_regex=nav_raw.get("version_dir_regex", ""),
            filter_artist_ids=nav_raw.get("filter_artist_ids", []),
            filter_category=nav_raw.get("filter_category", ""),
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
    """Load artists.yaml and .env, return a populated AppConfig.

    Args:
        yaml_path: Path to artists.yaml. Defaults to ``config/artists.yaml``.
        env_path: Path to .env file. Defaults to project root ``.env``.

    Returns:
        AppConfig with parsed artist list and env vars.

    Raises:
        FileNotFoundError: If yaml_path does not exist.
        yaml.YAMLError: If the YAML file is malformed.
    """
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
