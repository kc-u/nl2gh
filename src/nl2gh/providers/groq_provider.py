import json

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from ..prompts import get_system_prompt
from ..schemas import GitHubSearchArgs, TOOL_JSON_SCHEMA
from .base import BaseProvider

_TOOL = {
    "type": "function",
    "function": {
        "name": "search_github",
        "description": "Build a structured GitHub search query from natural language",
        "parameters": TOOL_JSON_SCHEMA,
    },
}


def _is_rate_limit(exc: BaseException) -> bool:
    return "429" in str(exc) or "rate_limit" in str(exc).lower()


class GroqProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self._client = Groq(api_key=api_key)
        self._model = model

    @property
    def model_id(self) -> str:
        return self._model

    @retry(
        retry=retry_if_exception(_is_rate_limit),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=10, max=60),
        reraise=True,
    )
    def query(self, nl_text: str) -> GitHubSearchArgs:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": nl_text},
            ],
            tools=[_TOOL],
            tool_choice={"type": "function", "function": {"name": "search_github"}},
        )

        message = response.choices[0].message
        if message.tool_calls:
            args = json.loads(message.tool_calls[0].function.arguments)
            return GitHubSearchArgs.model_validate(args)

        raise ValueError(f"{self._model} did not return a tool call")
