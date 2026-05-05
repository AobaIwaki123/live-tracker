"""navigation.type に応じた URL / API リクエストリストを生成する。(参照: docs/basic-design.md § 3. Navigation タイプ別 URL 生成ロジック)"""
from __future__ import annotations

import calendar
import datetime
from dataclasses import dataclass, field
from typing import Any

from dateutil.relativedelta import relativedelta

from src.config import ArtistConfig


@dataclass
class ApiRequest:
    """API エンドポイントへのリクエスト情報。

    Attributes:
        url: リクエスト先の完全 URL。
        method: HTTP メソッド（GET / POST など）。
        body: リクエストボディ。テンプレート展開済みの辞書。
        headers: リクエストヘッダー。
    """

    url: str
    method: str
    body: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class ScrapeTarget:
    """スクレイピング対象の 1 件分の情報。

    url と api のいずれか一方が設定される。

    Attributes:
        url: HTML スクレイピング用 URL。api_endpoint タイプでは None。
        api: API リクエスト情報。HTML タイプでは None。
        follow_next: True のとき GenericScraper が次ページリンクを辿る（pagination_links 用）。
        metadata: ターゲットに関する追加情報（例: 対象年月）。
    """

    url: str | None = None
    api: ApiRequest | None = None
    follow_next: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def _expand(value: Any, *, month: datetime.date) -> Any:
    """body_template や endpoint の値を月情報でテンプレート展開する。

    サポートするプレースホルダー:
    - ``{month_start}``: YYYY-MM-DD
    - ``{month_end}``: YYYY-MM-DD
    - ``{month_start_ms}``: Unix タイムスタンプ（ミリ秒）
    - ``{month_end_ms}``: Unix タイムスタンプ（ミリ秒）

    Args:
        value: テンプレート文字列（または任意の値）。
        month: 展開基準となる月。

    Returns:
        テンプレート展開後の文字列。文字列でなければ元の値をそのまま返す。
    """
    if not isinstance(value, str):
        return value

    month_start = month.replace(day=1)
    last_day = calendar.monthrange(month.year, month.month)[1]
    month_end = month.replace(day=last_day)

    # ミリ秒タイムスタンプ（日本時間 UTC+9 考慮のため 00:00:00 / 23:59:59 に合わせる）
    # TimeTree の例では utc_offset=32400 (9h) が別途送られているため
    # ここでは純粋な Unix タイムスタンプ（秒 * 1000）を生成する。
    start_ts = int(datetime.datetime.combine(month_start, datetime.time.min).timestamp() * 1000)
    end_ts = int(datetime.datetime.combine(month_end, datetime.time.max).timestamp() * 1000)

    return (
        value
        .replace("{month_start}", month_start.strftime("%Y-%m-%d"))
        .replace("{month_end}", month_end.strftime("%Y-%m-%d"))
        .replace("{month_start_ms}", str(start_ts))
        .replace("{month_end_ms}", str(end_ts))
        .replace("{year}", str(month.year))
        .replace("{month}", f"{month.month:02d}")
    )


def generate_targets(config: ArtistConfig) -> list[ScrapeTarget]:
    """ArtistConfig の navigation 設定からスクレイピング対象リストを生成する。

    navigation.type に応じて以下の挙動になる:

    - ``single_page``: ``config.base_url`` への 1 件のみ返す。
    - ``query_param``: ``range_months`` 分のクエリパラメータ付き URL を返す。
    - ``path_segment``: ``range_months`` 分のパスパターン展開 URL を返す。
    - ``pagination_links``: ``follow_next=True`` の 1 件のみ返す。次ページ追跡は GenericScraper が行う。
    - ``api_endpoint``: ``range_months`` 分の ApiRequest（body テンプレート展開済み）を返す。

    ``range_months`` が 0 以下の場合は空リストを返す。

    Args:
        config: アーティスト設定。navigation / base_url / base_url_origin を参照する。

    Returns:
        スクレイピング対象のリスト。要素数は navigation.type と range_months に依存する。

    Raises:
        ValueError: navigation.type が未知の値の場合。
    """
    nav = config.navigation

    if nav.range_months <= 0:
        return []

    today = datetime.date.today()
    months = [today + relativedelta(months=i) for i in range(nav.range_months)]

    match nav.type:
        case "single_page":
            return [ScrapeTarget(url=config.base_url, metadata={"date": today})]

        case "query_param":
            return [
                ScrapeTarget(
                    url=f"{config.base_url}?{nav.param}={m.strftime(nav.value_format)}",
                    metadata={"date": m},
                )
                for m in months
            ]

        case "path_segment":
            return [
                ScrapeTarget(
                    url=nav.pattern.format(
                        base_url=config.base_url,
                        base_url_origin=config.base_url_origin,
                        year=m.year,
                        month=m.month,
                    ),
                    metadata={"date": m},
                )
                for m in months
            ]

        case "pagination_links":
            return [ScrapeTarget(url=config.base_url, follow_next=True, metadata={"date": today})]

        case "api_endpoint":
            seen_urls: set[str] = set()
            targets: list[ScrapeTarget] = []
            for m in months:
                expanded_endpoint = _expand(nav.endpoint, month=m)
                # フルURLの場合はそのまま使用、相対パスの場合は origin を付与する
                if expanded_endpoint.startswith("http://") or expanded_endpoint.startswith("https://"):
                    api_url = expanded_endpoint
                else:
                    api_url = f"{config.base_url_origin}{expanded_endpoint}"
                # 同一 URL への重複リクエストを排除（年次ファイル等）
                if api_url in seen_urls:
                    continue
                seen_urls.add(api_url)
                targets.append(ScrapeTarget(
                    api=ApiRequest(
                        url=api_url,
                        method=nav.method,
                        body={k: _expand(v, month=m) for k, v in nav.body_template.items()},
                        headers=nav.headers,
                    ),
                    metadata={"date": m},
                ))
            return targets

        case _:
            raise ValueError(f"Unknown navigation type: {nav.type!r}")
