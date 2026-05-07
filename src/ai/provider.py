"""AI Provider 抽象クライアント — Claude / Gemini の切り替えを提供する。(参照: docs/basic-design.md § 4-0. AIProvider)"""

import os
from abc import ABC, abstractmethod


class ChatSession(ABC):
    """マルチターン会話セッションの抽象クラス。

    ``send`` を繰り返し呼ぶことで会話履歴が蓄積され、
    前のターンの文脈を保持したまま追加の質問ができる。
    """

    @abstractmethod
    def send(self, user: str) -> str:
        """ユーザーメッセージを送信し、モデルの応答テキストを返す。

        Args:
            user: ユーザーメッセージ。

        Returns:
            モデルの応答テキスト。
        """


class _ClaudeChatSession(ChatSession):
    """Claude Messages API を使うチャットセッション。"""

    def __init__(self, client, model: str, system: str) -> None:
        self._client = client
        self._model = model
        self._system = system
        self._messages: list[dict] = []

    def send(self, user: str) -> str:
        self._messages.append({"role": "user", "content": user})
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=self._system,
            messages=self._messages,
        )
        reply = msg.content[0].text or ""
        self._messages.append({"role": "assistant", "content": reply})
        return reply


class _GeminiChatSession(ChatSession):
    """Gemini chats API を使うチャットセッション。"""

    def __init__(self, client, system: str) -> None:
        from google.genai import types

        self._chat = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=system),
        )

    def send(self, user: str) -> str:
        response = self._chat.send_message(user)
        return response.text or ""


class AIProvider(ABC):
    """AI プロバイダーの抽象基底クラス。

    ``complete`` (1ショット) と ``chat_session`` (マルチターン) の
    2 メソッドを定義し、Claude / Gemini の差異を隠蔽する。
    """

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Send a prompt and return the model's response text.

        Args:
            system: システムプロンプト。
            user: ユーザープロンプト。

        Returns:
            モデルの応答テキスト。
        """

    @abstractmethod
    def chat_session(self, system: str) -> ChatSession:
        """マルチターン会話セッションを開始する。

        Args:
            system: セッション全体に適用するシステムプロンプト。

        Returns:
            ChatSession インスタンス。send() を繰り返し呼ぶことで
            会話履歴を維持したまま対話できる。
        """


class ClaudeProvider(AIProvider):
    """Anthropic Claude API を使う AIProvider 実装（モデル: claude-sonnet-4-6）。"""

    def __init__(self, api_key: str) -> None:
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-6"

    def complete(self, system: str, user: str) -> str:
        """Call Claude Messages API and return the first text block.

        Args:
            system: システムプロンプト。
            user: ユーザープロンプト。

        Returns:
            Claude の応答テキスト。空のとき空文字を返す。
        """
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text or ""

    def chat_session(self, system: str) -> ChatSession:
        """Claude マルチターンセッションを返す。

        Args:
            system: セッション全体のシステムプロンプト。

        Returns:
            _ClaudeChatSession インスタンス。
        """
        return _ClaudeChatSession(self.client, self.model, system)


class GeminiProvider(AIProvider):
    """Google Gemini API を使う AIProvider 実装（モデル: gemini-2.5-flash）。"""

    def __init__(self, api_key: str) -> None:
        from google import genai

        self.client = genai.Client(api_key=api_key)

    def complete(self, system: str, user: str) -> str:
        """Call Gemini generate_content API and return the response text.

        Args:
            system: システムプロンプト（user と結合して送信）。
            user: ユーザープロンプト。

        Returns:
            Gemini の応答テキスト。空のとき空文字を返す。
        """
        from google import genai  # noqa: F401 — keep import for type resolution

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{system}\n\n{user}",
        )
        return response.text or ""

    def chat_session(self, system: str) -> ChatSession:
        """Gemini マルチターンセッションを返す。

        Args:
            system: セッション全体のシステムプロンプト。

        Returns:
            _GeminiChatSession インスタンス。
        """
        return _GeminiChatSession(self.client, system)


def get_ai_provider() -> AIProvider:
    """Return an AIProvider instance based on the AI_PROVIDER env var.

    Selection priority:

    - ``AI_PROVIDER=claude``  → ClaudeProvider（ANTHROPIC_API_KEY 必須）
    - ``AI_PROVIDER=gemini``  → GeminiProvider（GEMINI_API_KEY 必須）
    - ``AI_PROVIDER=auto``    → ANTHROPIC_API_KEY があれば Claude、なければ Gemini

    Returns:
        設定に応じた AIProvider インスタンス。

    Raises:
        EnvironmentError: 対応する API キーが .env に設定されていない場合。
    """
    provider = os.environ.get("AI_PROVIDER", "auto").lower()

    if provider == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY または GEMINI_API_KEY のいずれかを .env に設定してください"
            )
        return ClaudeProvider(api_key=api_key)

    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY または GEMINI_API_KEY のいずれかを .env に設定してください"
            )
        return GeminiProvider(api_key=api_key)

    # auto mode — Anthropic keys always start with "sk-ant-"
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key.startswith("sk-ant-"):
        return ClaudeProvider(api_key=anthropic_key)

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        return GeminiProvider(api_key=gemini_key)

    raise EnvironmentError(
        "ANTHROPIC_API_KEY または GEMINI_API_KEY のいずれかを .env に設定してください"
    )
