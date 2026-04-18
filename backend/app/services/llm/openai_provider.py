import json

from pydantic import BaseModel, ValidationError

from app.core.exceptions import ProviderConfigurationError
from app.services.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, *, api_key: str, model: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency path
            raise ProviderConfigurationError(
                "OpenAI dependency not installed. Install the backend openai extra."
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete_structured(self, *, system_prompt: str, user_prompt: str, response_model: type[BaseModel]) -> BaseModel:
        response = self._client.responses.create(
            model=self._model,
            instructions=system_prompt,
            input=user_prompt,
        )
        raw_output = getattr(response, "output_text", None)
        if not raw_output:
            raise ProviderConfigurationError("OpenAI response did not contain text output")

        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError as exc:  # pragma: no cover - network path
            raise ProviderConfigurationError("OpenAI response was not valid JSON") from exc

        try:
            return response_model.model_validate(payload)
        except ValidationError as exc:  # pragma: no cover - network path
            raise ProviderConfigurationError("OpenAI response did not match expected schema") from exc
