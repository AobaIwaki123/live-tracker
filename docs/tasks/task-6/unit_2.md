# Unit M3-AB: ネットワークキャプチャ + AI サイト解析

## 概要
Playwright で XHR/Fetch ログを収集し、その結果を AI Provider（Claude または Gemini）に渡してサイトの Navigation 設定を生成する。
2つのコンポーネントを1ユニットとして実装する（キャプチャ結果が直接解析の入力になるため）。

---

## ブランチ・PR

```bash
git checkout -b feature/m3-site-analyzer
# 実装後
gh pr create --title "feat: ネットワークキャプチャ + AI サイト構造解析" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/analyzer/__init__.py` | 新規 |
| `src/analyzer/site_analyzer.py` | 新規 |

---

## 実装内容

### ネットワークキャプチャ部分

```python
@dataclass
class NetworkLog:
    url: str
    method: str
    request_body: str
    status: int
    response_body: str   # 先頭 2,000 字のみ

def capture_page(base_url: str) -> tuple[str, list[NetworkLog]]:
    """
    Playwright でページを開き HTML と XHR/Fetch ログを収集する。
    Returns: (html 先頭 20,000 字, ネットワークログ)
    """
    # schedule / event / live / api を含む URL のみフィルタ
    # 静的リソース（画像・CSS・フォント）は除外
```

### AI 解析部分

```python
ANALYSIS_SYSTEM_PROMPT = """
あなたは Web スクレイピング設定を生成する専門家です。
HTML とネットワークログから、スケジュール情報の取得方法を分析し、
指定の JSON Schema に従って設定を出力してください。

Navigation タイプの優先順位:
api_endpoint > query_param > path_segment > pagination_links > single_page
"""

def analyze_site(base_url: str, html: str, network_logs: list[NetworkLog]) -> SiteConfig:
    """
    AI Provider に解析を依頼し SiteConfig を返す。
    Claude / Gemini どちらを使うかは get_ai_provider() が決定する。
    """
    ai = get_ai_provider()
    prompt = _build_prompt(base_url, html, network_logs)
    raw_json = ai.complete(system=ANALYSIS_SYSTEM_PROMPT, user=prompt)
    return _parse_site_config(raw_json)
```

**AI への入力プロンプト構成:**
1. 現在の URL
2. ページ HTML（先頭 20,000 字）
3. キャプチャした XHR/Fetch リクエスト一覧
4. avam-fc.com の正解設定（Few-shot 例）
5. 出力 JSON Schema（厳密に指定）

**出力 JSON Schema:**
```json
{
  "fetch": { "dynamic": true },
  "navigation": {
    "type": "api_endpoint|query_param|path_segment|pagination_links|single_page",
    "range_months": 3
  },
  "response": {},
  "selectors": {},
  "detail": { "enabled": false }
}
```

---

## 統合後のインターフェース

```python
from src.analyzer.site_analyzer import capture_page, analyze_site, SiteConfig

html, logs = capture_page("https://avam-fc.com/schedule")
config: SiteConfig = analyze_site("https://avam-fc.com/schedule", html, logs)
```

---

## 人間の介入が必要な手順

- task-5/unit_2 で Playwright セットアップ済みであること
- `ANTHROPIC_API_KEY` または `GEMINI_API_KEY` のいずれかが `.env` に設定済みであること

---

## 依存タスク

- task-5（M2-P3 DynamicFetcher 完了 → Playwright 環境が整っている）
- task-2/unit_3（AI Provider クライアント）

## 並列実装可能なタスク

- task-6/unit_1（M2-P4 pagination_links 対応）と同時着手可能

---

## 完了条件

- [ ] avam-fc.com 解析時に `POST /api/schedule/get` が `network_logs` に含まれる
- [ ] 解析結果として `navigation.type: api_endpoint` / `endpoint: /api/schedule/get` が返る
- [ ] Claude / Gemini どちらで実行しても同等の出力が得られる
- [ ] 解析失敗時（API エラー・JSON パース失敗）にログを出してスキップする

---

## レビュー観点

- `capture_page()` が静的リソースを除外し、ネットワーク安定後に終了しているか（`networkidle`）
- AI 出力が JSON Schema に違反した場合に `ValueError` で検出できるか
- Few-shot 例がプロンプトに含まれているか（avam-fc.com の正解設定）
- Claude / Gemini で出力フォーマットが揃うか（プロンプトに明示的な JSON 出力指示があるか）
