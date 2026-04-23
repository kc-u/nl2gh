import json

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from ..prompts import get_system_prompt
from ..schemas import GitHubSearchArgs, TOOL_JSON_SCHEMA
from .base import BaseProvider

_FUNCTION_DECLARATION = {
    "name": "search_github",
    "description": "Build a structured GitHub search query from natural language",
    "parameters": TOOL_JSON_SCHEMA,
}


def _is_rate_limit(exc: BaseException) -> bool:
    return "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)


class GoogleProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-pro"):
        self._client = genai.Client(api_key=api_key)
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
        tool = types.Tool(function_declarations=[_FUNCTION_DECLARATION])
        config = types.GenerateContentConfig(
            system_instruction=get_system_prompt(),
            tools=[tool],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="ANY")
            ),
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=nl_text,
            config=config,
        )
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.function_call and part.function_call.name == "search_github":
                    return GitHubSearchArgs.model_validate(dict(part.function_call.args))

        return self._parse_json_fallback(response.text)

    def _parse_json_fallback(self, text: str) -> GitHubSearchArgs:
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1].lstrip("json").strip() if len(parts) > 1 else text
        try:
            return GitHubSearchArgs.model_validate(json.loads(text))
        except Exception:
            raise ValueError(
                f"{self._model} did not return a function call or valid JSON. "
                f"Response: {text[:200]}"
            )
