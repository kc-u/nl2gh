import json

from google import genai
from google.genai import types

from ..prompts import get_system_prompt
from ..schemas import GitHubSearchArgs, TOOL_JSON_SCHEMA
from .base import BaseProvider

_FUNCTION_DECLARATION = {
    "name": "search_github",
    "description": "Build a structured GitHub search query from natural language",
    "parameters": TOOL_JSON_SCHEMA,
}


class GoogleProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-pro"):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def model_id(self) -> str:
        return self._model

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

        # Extract function call
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.function_call and part.function_call.name == "search_github":
                    args = dict(part.function_call.args)
                    return GitHubSearchArgs.model_validate(args)

        # Fallback: model returned text — try JSON parse
        try:
            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text.strip())
            return GitHubSearchArgs.model_validate(data)
        except Exception:
            pass

        raise ValueError(
            f"{self._model} did not return a function call or valid JSON. "
            f"Raw response: {response.text[:200]}"
        )
