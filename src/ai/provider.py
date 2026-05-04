import os
from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Takes system prompt + user prompt, returns response text."""


class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str) -> None:
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-6"

    def complete(self, system: str, user: str) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text or ""


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str) -> None:
        from google import genai
        self.client = genai.Client(api_key=api_key)

    def complete(self, system: str, user: str) -> str:
        from google import genai  # noqa: F401 — keep import for type resolution
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{system}\n\n{user}",
        )
        return response.text or ""


def get_ai_provider() -> AIProvider:
    """
    Returns the appropriate AIProvider based on AI_PROVIDER env var.
    Priority:
      - AI_PROVIDER=claude  → ClaudeProvider (requires ANTHROPIC_API_KEY)
      - AI_PROVIDER=gemini  → GeminiProvider (requires GEMINI_API_KEY)
      - AI_PROVIDER=auto    → Claude if ANTHROPIC_API_KEY set, else Gemini if GEMINI_API_KEY set
    Raises EnvironmentError if no suitable key is found.
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

    # auto mode
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        return ClaudeProvider(api_key=anthropic_key)

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        return GeminiProvider(api_key=gemini_key)

    raise EnvironmentError(
        "ANTHROPIC_API_KEY または GEMINI_API_KEY のいずれかを .env に設定してください"
    )
