"""Playwright でページをキャプチャし AI でサイト構造を解析する。(参照: docs/basic-design.md § 4-1. SiteAnalyzer)"""

import json
import logging
import re
from dataclasses import dataclass, field

from playwright.sync_api import sync_playwright

from src.ai.provider import get_ai_provider

logger = logging.getLogger(__name__)

# スケジュール関連 URL のキーワード（XHR/Fetch ログのフィルタ条件）
_SCHEDULE_KEYWORDS = re.compile(r"schedule|event|live|api", re.IGNORECASE)

# 除外する静的リソースの拡張子
_STATIC_EXTENSIONS = re.compile(
    r"\.(js|css|png|jpg|jpeg|gif|webp|svg|ico|woff|woff2|ttf|eot|map)(\?.*)?$",
    re.IGNORECASE,
)

ANALYSIS_SYSTEM_PROMPT = """
あなたは Web スクレイピング設定を生成する専門家です。
HTML とネットワークログから、スケジュール情報の取得方法を分析し、
指定の JSON Schema に従って設定を出力してください。

Navigation タイプの優先順位:
api_endpoint > query_param > path_segment > pagination_links > single_page

### ガイドライン
1. **Astro/Next.js 等の動的URL**:
   URLにハッシュ（例: `260505...-AbCd...`）が含まれる場合、それはビルドごとに変わる一時的なディレクトリです。
   HTMLソースからその値を抽出するための正規表現を `navigation.version_dir_regex` に設定し、
   `endpoint` 内で `{version_dir}` プレースホルダーを使用してください。
2. **特殊なセレクタ記法**:
   `selectors` や `response.mapping` の値では以下の記法が使用可能です。
   - `::attr(name)`: 属性値を取得（例: `a::attr(href)`）
   - `::regex(pattern)`: 正規表現で抽出。グループ1を優先（例: `p::regex(開演\s*(\d+:\d+))`）
3. **APIレスポンスのネスト**:
   `response.mapping` ではドット記法（例: `schedule.start`）を使用してネストしたフィールドを取得できます。
4. **日付形式 (date_format)**:
   - レスポンスが Unix タイムスタンプ（ミリ秒）の場合は、`date_format` を空文字列 `""` に設定してください。
   - それ以外の場合は `%Y-%m-%d` 等の strftime 形式を指定してください。
5. **混在したデータのフィルタリング**:
   APIレスポンスに複数アーティストが混在している場合、`navigation.filter_artist_ids` や `navigation.filter_category` を活用して絞り込みを行ってください。

重要: 必ず JSON のみを出力してください。説明文やコードブロック記法（```json など）は一切含めないこと。
"""

# avam-fc.com の正解設定（Few-shot 例）
_FEW_SHOT_EXAMPLE = """\
### Few-shot 例 1: 標準的な API (https://avam-fc.com/schedule)

ネットワークログに POST /api/schedule/get が含まれる場合の正解設定:
```json
{
  "fetch": {"dynamic": true},
  "navigation": {
    "type": "api_endpoint",
    "endpoint": "/api/schedule/get",
    "method": "POST",
    "body_template": {"start": "{month_start}", "end": "{month_end}"},
    "range_months": 3
  },
  "response": {
    "format": "json_array",
    "array_path": "",
    "mapping": {"title": "title", "date": "reception_date", "date_format": "%Y-%m-%d"}
  },
  "selectors": {},
  "detail": {"enabled": false}
}
```

### Few-shot 例 2: Astro サイト & 特殊記法 (https://example.com/schedule)

ネットワークログに `https://example.com/json/260505...-AbCd.../2026_schedules.json` があり、
HTMLに `&quot;versionDir&quot;:&quot;260505...-AbCd...&quot;` が含まれる場合:
```json
{
  "fetch": {"dynamic": false},
  "navigation": {
    "type": "api_endpoint",
    "endpoint": "/json/{version_dir}/{year}_schedules.json",
    "method": "GET",
    "version_dir_regex": "&quot;versionDir&quot;:&quot;([^&]+)&quot;",
    "range_months": 3
  },
  "response": {
    "format": "json_object_with_array",
    "array_path": "items",
    "mapping": {
      "id": "id",
      "title": "title.content",
      "date": "start_at",
      "date_format": ""
    }
  },
  "selectors": {},
  "detail": {
    "enabled": true,
    "url_pattern": "{base_url_origin}/event/{id}",
    "selectors": {
      "venue": ".venue::regex(会場[:：]\s*(.+))",
      "ticket_url": "a.ticket-link::attr(href)"
    }
  }
}
```
"""

# 出力 JSON Schema の説明
_OUTPUT_SCHEMA = """\
### 出力 JSON Schema（このスキーマに厳密に従うこと）

{
  "fetch": {
    "dynamic": boolean  // Playwright が必要なら true
  },
  "navigation": {
    "type": "api_endpoint" | "query_param" | "path_segment" | "pagination_links" | "single_page",
    "range_months": integer,  // 何ヶ月先まで収集するか（1〜12）
    // api_endpoint の場合のみ:
    "endpoint": string,       // 例: "/api/schedule/get"
    "method": "GET" | "POST",
    "headers": object,        // オプション: 必要ならカスタムヘッダーを指定
    "body_template": object,  // POST ボディのテンプレート（{month_start}/{month_end} プレースホルダー使用可）
    "version_dir_regex": string, // オプション: Astro等でHTMLからハッシュを抽出する場合
    "filter_artist_ids": array,  // オプション: 数値配列。混在データからの絞り込み用
    "filter_category": string,   // オプション: カテゴリ名。混在データからの絞り込み用
    // query_param の場合のみ:
    "param": string,
    "value_format": string,   // strftime 形式 例: "%Y-%m-%d"
    "granularity": "monthly" | "weekly",
    // path_segment の場合のみ:
    "pattern": string         // 例: "{base_url}/{year}/{month:02d}"
  },
  "response": {
    // api_endpoint の場合のみ:
    "format": "json_array" | "json_object_with_array",
    "array_path": string,
    "mapping": {
      "id": string,
      "title": string,
      "date": string,
      "date_format": string
    }
  },
  "selectors": {
    // HTML スクレイピング型の場合のみ:
    "event_list": string,
    "title": string,
    "date": string,
    "venue": string,
    "ticket_url": string
  },
  "detail": {
    "enabled": boolean,
    // enabled が true の場合のみ:
    "url_pattern": string,
    "selectors": object
  }
}
"""


@dataclass
class NetworkLog:
    """XHR/Fetch リクエストの記録。

    Attributes:
        url: リクエスト URL。
        method: HTTP メソッド（GET / POST など）。
        request_body: リクエストボディ（先頭 2,000 字）。
        status: HTTP レスポンスステータスコード。
        response_body: レスポンスボディ（先頭 2,000 字）。
    """

    url: str
    method: str
    request_body: str
    status: int
    response_body: str


@dataclass
class SiteConfig:
    """AI が返すサイト設定。config/artists.yaml の fetch/navigation/response/selectors/detail に対応。

    Attributes:
        fetch: フェッチ設定。例: {"dynamic": True}
        navigation: ナビゲーション設定。type / endpoint / range_months など。
        response: レスポンス解釈設定（api_endpoint タイプで使用）。
        selectors: CSS セレクタ設定（HTML スクレイピング型で使用）。
        detail: 詳細ページ設定。{"enabled": bool, ...}
    """

    fetch: dict = field(default_factory=dict)
    navigation: dict = field(default_factory=dict)
    response: dict = field(default_factory=dict)
    selectors: dict = field(default_factory=dict)
    detail: dict = field(default_factory=dict)


def capture_page(base_url: str) -> tuple[str, list[NetworkLog]]:
    """Playwright でページを開き HTML と XHR/Fetch ログを収集する。

    スケジュール / イベント / ライブ / API に関連するネットワークリクエストのみを
    記録し、画像・CSS・フォントなどの静的リソースは除外する。
    ネットワーク安定（networkidle）を待ってから HTML を取得する。

    Args:
        base_url: 解析対象サイトの URL。

    Returns:
        (HTML 先頭 20,000 字, キャプチャしたネットワークログのリスト) のタプル。
    """
    logs: list[NetworkLog] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # レスポンスボディを保持するための一時バッファ
        # {request_id: NetworkLog} — response イベント受信時に response_body を補完する
        _pending: dict[str, NetworkLog] = {}

        def _on_request(request) -> None:
            url = request.url
            # 静的リソースは除外
            if _STATIC_EXTENSIONS.search(url):
                return
            # スケジュール関連キーワードを含む URL のみ対象
            if not _SCHEDULE_KEYWORDS.search(url):
                return
            try:
                body = request.post_data or ""
            except Exception:
                body = ""
            log = NetworkLog(
                url=url,
                method=request.method,
                request_body=body[:2000],
                status=0,
                response_body="",
            )
            _pending[request.url + request.method] = log

        def _on_response(response) -> None:
            key = response.url + response.request.method
            log = _pending.pop(key, None)
            if log is None:
                return
            log.status = response.status
            try:
                body = response.text()
                log.response_body = body[:2000]
            except Exception:
                log.response_body = ""
            logs.append(log)

        page.on("request", _on_request)
        page.on("response", _on_response)

        page.goto(base_url, wait_until="networkidle", timeout=60000)
        html = page.content()

        browser.close()

    return html[:20000], logs


def analyze_site(base_url: str, html: str, network_logs: list[NetworkLog]) -> SiteConfig | None:
    """AI Provider に解析を依頼し SiteConfig を返す。

    Claude / Gemini どちらを使うかは get_ai_provider() が決定する。
    解析失敗時（API エラー・JSON パース失敗・スキーマ違反）はログを出して None を返す。

    Args:
        base_url: 解析対象サイトの URL。
        html: ページ HTML（先頭 20,000 字）。
        network_logs: capture_page() で取得したネットワークログ。

    Returns:
        解析に成功した場合は SiteConfig、失敗した場合は None。
    """
    try:
        ai = get_ai_provider()
        prompt = _build_prompt(base_url, html, network_logs)
        raw_json = ai.complete(system=ANALYSIS_SYSTEM_PROMPT, user=prompt)
        return _parse_site_config(raw_json)
    except Exception as exc:
        logger.error("サイト解析に失敗しました（%s）: %s", base_url, exc)
        return None


def _build_prompt(base_url: str, html: str, network_logs: list[NetworkLog]) -> str:
    """AI へ渡す解析プロンプトを構築する。

    Args:
        base_url: 解析対象サイトの URL。
        html: ページ HTML（先頭 20,000 字）。
        network_logs: キャプチャしたネットワークログ。

    Returns:
        AI へ渡すプロンプト文字列。
    """
    logs_text = _format_network_logs(network_logs)

    return f"""\
## 解析対象 URL
{base_url}

## ページ HTML（先頭 20,000 字）
```html
{html}
```

## キャプチャした XHR/Fetch リクエスト一覧
{logs_text}

{_FEW_SHOT_EXAMPLE}

{_OUTPUT_SCHEMA}

上記の情報をもとに、このサイトのスケジュール情報取得設定を JSON で出力してください。
JSON のみを出力し、説明文やコードブロック記法（```json など）は含めないこと。
"""


def _format_network_logs(logs: list[NetworkLog]) -> str:
    if not logs:
        return "（XHR/Fetch リクエストなし）"
    lines = []
    for log in logs:
        lines.append(f"- [{log.method}] {log.url} (status={log.status})")
        if log.request_body:
            lines.append(f"  Request body: {log.request_body[:500]}")
        if log.response_body:
            lines.append(f"  Response body (先頭): {log.response_body[:300]}")
    return "\n".join(lines)


def _parse_site_config(raw_json: str) -> SiteConfig:
    """AI が返した JSON 文字列を SiteConfig に変換する。

    Args:
        raw_json: AI が返した JSON 文字列。コードブロックが含まれていても除去して処理する。

    Returns:
        パースした SiteConfig。

    Raises:
        ValueError: JSON が不正またはスキーマに違反している場合。
    """
    # AI がコードブロックを付けて返した場合に除去する
    cleaned = raw_json.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI の出力が JSON としてパースできませんでした: {exc}\n出力: {cleaned[:500]}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"AI の出力が dict ではありません: {type(data)}")

    # 必須フィールドの存在チェック
    for required_key in ("fetch", "navigation", "detail"):
        if required_key not in data:
            raise ValueError(f"必須フィールドが不足しています: '{required_key}' が見つかりません")

    navigation = data.get("navigation", {})
    nav_type = navigation.get("type")
    valid_types = {"api_endpoint", "query_param", "path_segment", "pagination_links", "single_page"}
    if nav_type not in valid_types:
        raise ValueError(
            f"navigation.type が不正な値です: '{nav_type}'. "
            f"有効な値: {', '.join(sorted(valid_types))}"
        )

    return SiteConfig(
        fetch=data.get("fetch", {}),
        navigation=navigation,
        response=data.get("response", {}),
        selectors=data.get("selectors", {}),
        detail=data.get("detail", {}),
    )
