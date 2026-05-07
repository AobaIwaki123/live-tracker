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

# イベント要素スニペット抽出用キーワード（クラス名マッチ）
_EVENT_SNIPPET_PATTERN = re.compile(
    r"schedule|event|live|match|game|calendar|concert|ticket",
    re.IGNORECASE,
)

# 除外する静的リソースの拡張子
_STATIC_EXTENSIONS = re.compile(
    r"\.(js|css|png|jpg|jpeg|gif|webp|svg|ico|woff|woff2|ttf|eot|map)(\?.*)?$",
    re.IGNORECASE,
)

# analyze_site() でのフォローアップターン上限（Turn 1 を含まない）
_MAX_FOLLOWUP_TURNS = 2

# analyze_site() でのバリデーションターン上限
_MAX_VALIDATION_TURNS = 2

ANALYSIS_SYSTEM_PROMPT = """
あなたは Web スクレイピング設定を生成する専門家です。
HTML とネットワークログから、スケジュール情報の取得方法を分析し、
指定の JSON Schema に従って設定を出力してください。

### Navigation タイプの選択基準（重要）

**api_endpoint を選択する条件（すべてを満たすこと）**:
- ネットワークログにスケジュールデータを返す XHR/Fetch リクエストが実際に含まれること
- そのレスポンスが JSON 形式でスケジュール情報（タイトル・日付を含む）を返していること
- HTML 本体にはスケジュールデータが含まれておらず、JS によって動的に取得されていること

**HTML スクレイピング（path_segment / query_param / single_page 等）を優先する条件**:
- HTML ソースに `<li>` や `<div>` 等でイベントが直接列挙されている場合
- ネットワークログに明確なスケジュール API が存在しない場合
- curl 等でも取得できる静的 HTML にスケジュールが含まれている場合

優先順位: 実証された api_endpoint > path_segment > query_param > pagination_links > single_page

### ガイドライン
1. **Astro/Next.js 等の動的URL**:
   URLにハッシュ（例: `260505...-AbCd...`）が含まれる場合、それはビルドごとに変わる一時的なディレクトリです。
   HTMLソースからその値を抽出するための正規表現を `navigation.version_dir_regex` に設定し、
   `endpoint` 内で `{version_dir}` プレースホルダーを使用してください。
2. **特殊なセレクタ記法**:
   `selectors` や `response.mapping` の値では以下の記法が使用可能です。
   - `::attr(name)`: 属性値を取得（例: `a::attr(href)`）
   - `::regex(pattern)`: 正規表現で抽出。グループ1を優先（例: `p::regex(開演\\s*(\\d+:\\d+))`）
3. **APIレスポンスのネスト**:
   `response.mapping` ではドット記法（例: `schedule.start`）を使用してネストしたフィールドを取得できます。
4. **日付形式 (date_format)**:
   - レスポンスが Unix タイムスタンプ（ミリ秒）の場合は、`date_format` を空文字列 `""` に設定してください。
   - それ以外の場合は `%Y-%m-%d` 等の strftime 形式を指定してください。
   - HTML に月・日のみ（年なし）で日付が書かれている場合は `date_format: "%d"` を使用し、年月はURLのクエリパラメータから補完できます。
5. **混在したデータのフィルタリング**:
   APIレスポンスに複数アーティストが混在している場合、`navigation.filter_artist_ids` や `navigation.filter_category` を活用して絞り込みを行ってください。
6. **Fanplus プラットフォーム (*.asobisystem.com 等)**:
   これらのサイトはサーバーサイド HTML レンダリングを使用します。API らしいログがあっても
   スケジュールデータが HTML に直接含まれている場合は HTML スクレイピングを選択してください。
   典型的なパターン: `navigation.type: path_segment`、
   `pattern: "{base_url_origin}/live_information/schedule/list/?year={year}&month={month:02d}"`、
   `event_list: li.sys-schedule a.box_live_2`、`title: p.tit`、`date: span.block--date__date`、`date_format: "%d"`

重要: 必ず JSON のみを出力してください。説明文やコードブロック記法（```json など）は一切含めないこと。
"""

# avam-fc.com / Fanplus / Astro の正解設定（Few-shot 例）
_FEW_SHOT_EXAMPLE = """\
### Few-shot 例 1: 実証された API (https://avam-fc.com/schedule)

ネットワークログに `POST /api/schedule/get` が含まれ、
レスポンスボディが `[{"title": "...", "reception_date": "2026-05-01", ...}]` のような
スケジュール JSON 配列を返している場合:
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

### Few-shot 例 2: Fanplus プラットフォーム HTML (https://example.asobisystem.com/live_information/schedule)

HTML に `<li class="sys-schedule"><a class="box box_live_2">...` が直接含まれ、
スケジュールデータが静的 HTML として配信されている場合（API ログがあっても HTML を優先）:
```json
{
  "fetch": {"dynamic": false},
  "navigation": {
    "type": "path_segment",
    "pattern": "{base_url_origin}/live_information/schedule/list/?year={year}&month={month:02d}",
    "range_months": 3
  },
  "response": {},
  "selectors": {
    "event_list": "li.sys-schedule a.box_live_2",
    "id": "::attr(href)",
    "title": "p.tit",
    "date": "span.block--date__date",
    "date_format": "%d"
  },
  "detail": {"enabled": false}
}
```

### Few-shot 例 3: Astro サイト & 特殊記法 (https://example.com/schedule)

ネットワークログに `https://example.com/json/260505...-AbCd.../2026_schedules.json` があり、
レスポンスが `{"items": [...]}` 形式のスケジュール JSON で、
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
      "venue": ".venue::regex(会場[:：]\\s*(.+))",
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
    "date_format": string,  // 必須。日付文字列のフォーマット。例: "%Y-%m-%d" / "%d" / "%Y/%m/%d"
                            // YYYY-MM-DD など標準フォーマットなら "" (空文字)
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

    return html, logs


def analyze_site(base_url: str, html: str, network_logs: list[NetworkLog]) -> SiteConfig | None:
    """AI Provider に解析を依頼し SiteConfig を返す。

    3 フェーズのループで精度を高める:

    Phase 1 — Turn 1: HTML + ネットワークログ + スニペットから初期設定を生成。
    Phase 2 — 完全性チェック: 必須フィールドが欠けていれば補完ターンを繰り返す（最大 _MAX_FOLLOWUP_TURNS 回）。
    Phase 3 — バリデーション: 実際の URL をフェッチしてイベント 0 件なら AI に
              ターゲット URL のスニペットを渡して再修正（最大 _MAX_VALIDATION_TURNS 回）。

    Claude / Gemini どちらを使うかは get_ai_provider() が決定する。

    Args:
        base_url: 解析対象サイトの URL。
        html: capture_page() で取得したフル HTML。
        network_logs: capture_page() で取得したネットワークログ。

    Returns:
        解析に成功した場合は SiteConfig、失敗した場合は None。
    """
    try:
        ai = get_ai_provider()
        session = ai.chat_session(ANALYSIS_SYSTEM_PROMPT)

        # Phase 1: Turn 1 — HTML + ネットワークログ全体を渡して初期設定を取得
        prompt = _build_prompt(base_url, html, network_logs)
        raw_json = session.send(prompt)
        site_config = _parse_site_config(raw_json)
        logger.info("ターン 1 完了: %s", site_config.navigation.get("type"))

        # Phase 2: 不足フィールドを補完するまでループ
        for turn in range(2, _MAX_FOLLOWUP_TURNS + 2):
            missing = _check_completeness(site_config)
            if not missing:
                logger.info("完全性チェック OK（%d ターン）", turn - 1)
                break
            logger.info("ターン %d: 不完全なフィールド: %s", turn, missing)
            follow_up = _build_followup_prompt(missing, site_config)
            raw_json = session.send(follow_up)
            updated = _parse_site_config(raw_json)
            site_config = _merge_configs(site_config, updated)
        else:
            remaining = _check_completeness(site_config)
            if remaining:
                logger.warning("完全性チェック: 未解決フィールド: %s", remaining)

        # Phase 3: 実スクレイプで 0 件なら AI にフィードバックして再修正
        for vturn in range(1, _MAX_VALIDATION_TURNS + 1):
            count, val_snippets = _validate_config(site_config, base_url)
            if count < 0:
                logger.info("バリデーションスキップ（%s）", site_config.navigation.get("type"))
                break
            if count > 0:
                logger.info("バリデーション成功: %d 件取得（バリデーションターン %d）", count, vturn)
                break
            logger.info("バリデーションターン %d: 0 件 — AI に実ページ HTML をフィードバック", vturn)
            feedback = _build_validation_feedback(site_config, base_url, val_snippets)
            raw_json = session.send(feedback)
            updated = _parse_site_config(raw_json)
            site_config = _merge_configs(site_config, updated)
        else:
            count, _ = _validate_config(site_config, base_url)
            if count == 0:
                logger.warning("バリデーション: 最大ターン数に達しました。0 件のまま確定")

        return site_config
    except Exception as exc:
        logger.error("サイト解析に失敗しました（%s）: %s", base_url, exc)
        return None


def _build_validation_url(site_config: SiteConfig, base_url: str) -> str | None:
    """バリデーション用の最初の URL を構築する。

    api_endpoint タイプは検証が複雑なためスキップ（None を返す）。

    Args:
        site_config: 検証対象の SiteConfig。
        base_url: アーティストの base_url。

    Returns:
        フェッチ対象 URL。スキップ対象のときは None。
    """
    import datetime
    from urllib.parse import urlparse

    nav = site_config.navigation
    nav_type = nav.get("type")

    if nav_type == "api_endpoint":
        return None

    parsed = urlparse(base_url)
    base_url_origin = f"{parsed.scheme}://{parsed.netloc}"
    today = datetime.date.today()

    if nav_type in ("single_page", "pagination_links"):
        return base_url

    if nav_type == "path_segment":
        pattern = nav.get("pattern", "")
        url = pattern.format(
            base_url=base_url,
            base_url_origin=base_url_origin,
            year=today.year,
            month=today.month,
        )
        if not url.startswith("http"):
            url = f"{base_url_origin}{url}"
        return url

    if nav_type == "query_param":
        param = nav.get("param", "")
        value_format = nav.get("value_format", "%Y-%m")
        return f"{base_url}?{param}={today.strftime(value_format)}"

    return None


def _validate_config(site_config: SiteConfig, base_url: str) -> tuple[int, str]:
    """実際に 1 URL をフェッチして event_list セレクタで取れる要素数を確認する。

    Args:
        site_config: 検証対象の SiteConfig。
        base_url: アーティストの base_url（URL 構築に使用）。

    Returns:
        (element_count, snippets):
        element_count が -1 のときは検証スキップ。
        snippets は 0 件のとき AI へのフィードバック用スニペット。
    """
    url = _build_validation_url(site_config, base_url)
    if url is None:
        return -1, ""

    event_list_selector = site_config.selectors.get("event_list", "")
    if not event_list_selector:
        return -1, ""

    try:
        dynamic = site_config.fetch.get("dynamic", False)
        if dynamic:
            from scrapling.fetchers import DynamicFetcher
            page = DynamicFetcher().fetch(url, timeout=30000)
        else:
            from scrapling.fetchers import Fetcher
            page = Fetcher().get(url, timeout=30)

        if page is None:
            return -1, ""

        elements = page.css(event_list_selector)
        count = len(elements)

        page_html = page.html if hasattr(page, "html") else ""
        snippets = _extract_event_snippets(page_html) if count == 0 else ""
        return count, snippets

    except Exception as exc:
        logger.warning("バリデーションフェッチ失敗 (%s): %s", url, exc)
        return -1, ""


def _build_validation_feedback(
    site_config: SiteConfig, base_url: str, val_snippets: str
) -> str:
    """バリデーション 0 件時の AI フィードバックプロンプトを構築する。

    Args:
        site_config: 現在の SiteConfig。
        base_url: アーティストの base_url。
        val_snippets: バリデーション URL から抽出したスニペット。

    Returns:
        フィードバックプロンプト文字列。
    """
    url = _build_validation_url(site_config, base_url) or base_url
    current_json = json.dumps(
        {
            "fetch": site_config.fetch,
            "navigation": site_config.navigation,
            "response": site_config.response,
            "selectors": site_config.selectors,
            "detail": site_config.detail,
        },
        ensure_ascii=False,
        indent=2,
    )

    return f"""\
現在の設定で実際にスクレイプしたところ、イベントが 0 件でした。

対象 URL: {url}
使用した event_list セレクタ: {site_config.selectors.get('event_list', '（未設定）')}

現在の設定:
```json
{current_json}
```

対象 URL のページから抽出した実要素スニペット（この HTML を元にセレクタを修正してください）:
{val_snippets}

0 件になった原因（セレクタの不一致 / navigation.pattern の誤り など）を特定し、
修正した完全な JSON を出力してください。JSON のみを出力してください。
"""


def _check_completeness(config: SiteConfig) -> list[str]:
    """SiteConfig の必須フィールドを検査し、不足しているフィールドパスを返す。

    Args:
        config: 検査対象の SiteConfig。

    Returns:
        不足フィールドのパス一覧。空リストなら完全。
    """
    missing: list[str] = []
    nav_type = config.navigation.get("type")

    if not nav_type:
        missing.append("navigation.type")
        return missing

    if nav_type == "api_endpoint":
        if not config.navigation.get("endpoint"):
            missing.append("navigation.endpoint")
        if not config.navigation.get("method"):
            missing.append("navigation.method")
        mapping = config.response.get("mapping", {})
        if not mapping.get("title"):
            missing.append("response.mapping.title")
        if not mapping.get("date"):
            missing.append("response.mapping.date")
        if "date_format" not in mapping:
            missing.append("response.mapping.date_format")

    elif nav_type == "query_param":
        if not config.navigation.get("param"):
            missing.append("navigation.param")
        if not config.navigation.get("value_format"):
            missing.append("navigation.value_format")
        if not config.selectors.get("event_list"):
            missing.append("selectors.event_list")
        if not config.selectors.get("title"):
            missing.append("selectors.title")
        if not config.selectors.get("date"):
            missing.append("selectors.date")
        if "date_format" not in config.selectors:
            missing.append("selectors.date_format")

    elif nav_type == "path_segment":
        if not config.navigation.get("pattern"):
            missing.append("navigation.pattern")
        if not config.selectors.get("event_list"):
            missing.append("selectors.event_list")
        if not config.selectors.get("title"):
            missing.append("selectors.title")
        if not config.selectors.get("date"):
            missing.append("selectors.date")
        if "date_format" not in config.selectors:
            missing.append("selectors.date_format")

    else:  # single_page / pagination_links
        if not config.selectors.get("event_list"):
            missing.append("selectors.event_list")
        if not config.selectors.get("title"):
            missing.append("selectors.title")
        if not config.selectors.get("date"):
            missing.append("selectors.date")
        if "date_format" not in config.selectors:
            missing.append("selectors.date_format")

    if not config.navigation.get("range_months"):
        missing.append("navigation.range_months")

    return missing


def _merge_configs(original: SiteConfig, updated: SiteConfig) -> SiteConfig:
    """original に updated の非空フィールドをマージして返す。

    updated の各フィールドが空でなければ original を上書きする。
    dict 値はキーレベルでマージし、updated の非空値が優先される。

    Args:
        original: ベースとなる SiteConfig。
        updated: フォローアップターンで得た SiteConfig。

    Returns:
        マージ結果の新しい SiteConfig。
    """
    def _merge_dict(orig: dict, upd: dict) -> dict:
        if not upd:
            return orig
        if not orig:
            return upd
        merged = dict(orig)
        for k, v in upd.items():
            if v is not None:  # None のみ「未設定」として扱い、""・0・False は有効値として保持
                merged[k] = v
        return merged

    return SiteConfig(
        fetch=_merge_dict(original.fetch, updated.fetch),
        navigation=_merge_dict(original.navigation, updated.navigation),
        response=_merge_dict(original.response, updated.response),
        selectors=_merge_dict(original.selectors, updated.selectors),
        detail=_merge_dict(original.detail, updated.detail),
    )


def _build_followup_prompt(missing: list[str], current: SiteConfig) -> str:
    """不足フィールドを補完するためのフォローアッププロンプトを構築する。

    Args:
        missing: _check_completeness() が返した不足フィールドパス一覧。
        current: 現時点の SiteConfig（AI への参考情報として渡す）。

    Returns:
        フォローアップターン用のプロンプト文字列。
    """
    current_json = json.dumps(
        {
            "fetch": current.fetch,
            "navigation": current.navigation,
            "response": current.response,
            "selectors": current.selectors,
            "detail": current.detail,
        },
        ensure_ascii=False,
        indent=2,
    )
    missing_list = "\n".join(f"- {f}" for f in missing)

    return f"""\
以下のフィールドが不完全または未設定です:
{missing_list}

現在の設定（参考）:
```json
{current_json}
```

HTML とネットワークログを再確認し、不足フィールドをすべて補完した完全な JSON を出力してください。
JSON のみを出力し、説明文やコードブロック記法（```json など）は含めないこと。
"""


def _extract_event_snippets(html: str) -> str:
    """HTML からイベント関連要素のスニペットを抽出する。

    クラス名に _EVENT_SNIPPET_PATTERN のキーワードを含む要素を探し、
    出現回数が多い順（繰り返しリストアイテム優先）に最大 5 タイプを抽出する。
    body/html/head および outerHTML が 3,000 字超の大型コンテナは除外する。

    Args:
        html: ページ HTML 文字列（フル HTML を想定）。

    Returns:
        抽出したスニペットの文字列。要素が見つからない場合は説明文を返す。
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # (tag_name, frozenset(classes)) -> [element, ...]
    grouped: dict[tuple, list] = {}
    for tag in soup.find_all(class_=_EVENT_SNIPPET_PATTERN):
        if tag.name in ("body", "html", "head"):
            continue
        # outerHTML が大きすぎる要素はコンテナと判断して除外
        if len(str(tag)) > 3000:
            continue
        key = (tag.name, frozenset(tag.get("class", [])))
        grouped.setdefault(key, []).append(tag)

    if not grouped:
        return "（イベント関連クラスの要素が見つかりませんでした）"

    # 出現回数が多い順（繰り返し要素 = リストアイテム候補）
    sorted_groups = sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)

    parts: list[str] = []
    for (tag_name, classes), elements in sorted_groups[:5]:
        class_str = ".".join(sorted(classes))
        for elem in elements[:2]:
            outer = str(elem)[:1500]
            parts.append(f"<!-- {tag_name}.{class_str} ({len(elements)}件) -->\n{outer}")

    return "\n\n".join(parts)


def _load_artist_examples() -> str:
    """config/artists.yaml から動作確認済みの設定を few-shot 例テキストとして返す。

    Returns:
        フォーマット済みの例文字列。読み込み失敗時は空文字。
    """
    from pathlib import Path
    import yaml as _yaml

    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "artists.yaml"
    if not config_path.exists():
        return ""

    try:
        with open(config_path, encoding="utf-8") as f:
            data = _yaml.safe_load(f)

        artists = [a for a in data.get("artists", []) if a.get("analyzed_at") and a.get("navigation")]
        if not artists:
            return ""

        lines = [
            "### 動作確認済みの既存設定（参考）",
            "以下は実際に稼働している設定です。同様のサイト構造・プラットフォームの場合は参考にしてください。",
            "",
        ]
        for artist in artists:
            name = artist.get("display_name") or artist.get("name", "?")
            base_url = artist.get("base_url", "")
            config = {k: artist[k] for k in ("fetch", "navigation", "response", "selectors", "detail") if k in artist}
            lines.append(f"#### [{name}] {base_url}")
            lines.append("```json")
            lines.append(json.dumps(config, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

        return "\n".join(lines)
    except Exception as exc:
        logger.warning("既存設定の読み込みに失敗しました: %s", exc)
        return ""


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
    # スニペットはフル HTML から抽出し、AI に渡す HTML 本文は 20,000 字に制限する
    snippets_text = _extract_event_snippets(html)
    html_for_prompt = html[:20000]
    existing_examples = _load_artist_examples()

    return f"""\
## 解析対象 URL
{base_url}

## ページ HTML（先頭 20,000 字）
```html
{html_for_prompt}
```

## キャプチャした XHR/Fetch リクエスト一覧
{logs_text}

## イベント要素スニペット（クラス名にスケジュール関連キーワードを含む実要素）
以下は実際のページから抽出した HTML 断片です。
`selectors` の値はこのスニペットに存在するタグ・クラス名のみを使って導出してください。
存在しないクラス名やタグ名を推測で使わないこと。

{snippets_text}

{_FEW_SHOT_EXAMPLE}

{existing_examples}

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
