import anthropic

from ..prompts import get_system_prompt
from ..schemas import GitHubSearchArgs, TOOL_JSON_SCHEMA
from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @property
    def model_id(self) -> str:
        return self._model

    def query(self, nl_text: str) -> GitHubSearchArgs:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=get_system_prompt(),
            tools=[
                {
                    "name": "search_github",
                    "description": "Build a structured GitHub search query from natural language",
                    "input_schema": TOOL_JSON_SCHEMA,
                }
            ],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": nl_text}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "search_github":
                return GitHubSearchArgs.model_validate(block.input)

        raise ValueError(f"{self._model} did not return a tool call")
