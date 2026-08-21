"""Ollama-backed text summarization."""

from ollama import AsyncClient, ResponseError

from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL


class OllamaSummaryProvider:
    """Generate concise summaries through a local Ollama service."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        client: AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._client = client or AsyncClient(host=base_url)

    async def summarize(self, text: str) -> str:
        """Return a concise, factual summary of the supplied text."""
        response = await self._client.chat(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the user's text concisely and factually.",
                },
                {"role": "user", "content": text},
            ],
            options={"temperature": 0.2},
        )
        summary = response.message.content.strip()
        if not summary:
            raise ValueError("Ollama returned an empty summary")
        return summary


def is_transient_ollama_error(error: Exception) -> bool:
    """Return whether an Ollama failure is safe to retry."""
    if isinstance(error, (ConnectionError, TimeoutError)):
        return True
    return isinstance(error, ResponseError) and 500 <= error.status_code < 600
