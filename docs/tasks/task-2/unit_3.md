# Unit AI-P0: AI Provider 抽象クライアント

## 概要
Claude API と Gemini API を同一インターフェースで扱う抽象クライアントを実装する。
どちらか一方の API キーが設定されていれば動作する。
M3-P2（サイト解析）と M3-P5（エンリッチメント）の両方から利用される。

---

## ブランチ・PR

```bash
git checkout -b feature/ai-provider-client
# 実装後
gh pr create --title "feat: AI Provider 抽象クライアント（Claude / Gemini 切り替え）" --base main
```

---

## 対象ファイル

| ファイル | 新規/更新 |
|---|---|
| `src/ai/__init__.py` | 新規 |
| `src/ai/provider.py` | 新規 |
| `.env.example` | 更新 |
| `requirements.txt` | 更新（`google-generativeai` 追加） |

---

## 実装内容

```python
class AIProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """システムプロンプト + ユーザープロンプトを受け取りテキストを返す"""

class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-6"

    def complete(self, system: str, user: str) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

class GeminiProvider(AIProvider):
    def __init__(self, api_key: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def complete(self, system: str, user: str) -> str:
        response = self.model.generate_content(f"{system}\n\n{user}")
        return response.text

def get_ai_provider() -> AIProvider:
    """
    環境変数 AI_PROVIDER に従いインスタンスを返す。
    AI_PROVIDER 未設定の場合、設定済みキーを自動検出する。
    """
    provider = os.getenv("AI_PROVIDER", "auto").lower()

    if provider in ("claude", "auto") and os.getenv("ANTHROPIC_API_KEY"):
        return ClaudeProvider(os.environ["ANTHROPIC_API_KEY"])
    if provider in ("gemini", "auto") and os.getenv("GEMINI_API_KEY"):
        return GeminiProvider(os.environ["GEMINI_API_KEY"])

    raise EnvironmentError(
        "ANTHROPIC_API_KEY または GEMINI_API_KEY のいずれかを .env に設定してください"
    )
```

**`.env.example` に追記する内容**
```
# AI Provider（claude または gemini、省略時は設定済みキーを自動検出）
AI_PROVIDER=claude

# どちらか一方が設定されていれば動作する
ANTHROPIC_API_KEY=sk-ant-xxxxx
GEMINI_API_KEY=AIzaxxx
```

---

## 統合後のインターフェース

```python
from src.ai.provider import get_ai_provider, AIProvider

ai: AIProvider = get_ai_provider()
result: str = ai.complete(system="...", user="...")
```

---

## 人間の介入が必要な手順

1. Claude を使う場合: `ANTHROPIC_API_KEY` を `.env` に設定
2. Gemini を使う場合: `GEMINI_API_KEY` を `.env` に設定
3. どちらも設定する場合は `AI_PROVIDER=claude` または `AI_PROVIDER=gemini` で優先順位を指定

---

## 依存タスク

- task-1/unit_1（M1-P1: 設定ロードの仕組みが必要）

## 並列実装可能なタスク

- task-2/unit_1（Notion Client）と同時着手可能
- task-2/unit_2（HTML スクレイパー）と同時着手可能

---

## 完了条件

- [ ] `ANTHROPIC_API_KEY` のみ設定時に Claude が使われる
- [ ] `GEMINI_API_KEY` のみ設定時に Gemini が使われる
- [ ] 両方設定時に `AI_PROVIDER` 環境変数で切り替えられる
- [ ] どちらも未設定時に分かりやすいエラーが出る
- [ ] `ai.complete("test system", "hello")` が文字列を返す

---

## レビュー観点

- どちらの API も未設定のとき `EnvironmentError` が分かりやすいメッセージで上がるか
- `GeminiProvider` のモデル名が最新版（`gemini-2.0-flash`）か
- `ClaudeProvider` のモデル名が最新版（`claude-sonnet-4-6`）か
- `complete()` のレスポンスが空文字の場合のハンドリング
