"""Cloud provider registry and one adapter per OpenAI-compatible API family."""

import os
from dataclasses import dataclass

from openai import OpenAI

TIMEOUT_SECONDS = 3600
# A chat completion carries no status field; derive one from finish_reason instead.
COMPLETION_STATUS = {"stop": "completed", "length": "incomplete"}


@dataclass(frozen=True)
class Provider:
    key: str
    model: str
    api: str
    base_url: str
    env_var: str
    runtime: str


PROVIDERS = {
    "luna": Provider(
        key="luna",
        model="gpt-5.6-luna",
        api="responses",
        base_url="https://api.openai.com/v1",
        env_var="openai_secret_key",
        runtime="openai_responses",
    ),
    "motif3": Provider(
        key="motif3",
        model="motif/motif-3",
        api="chat_completions",
        base_url="https://api-cbt.morphfactory.io/v1",
        env_var="morph_secret_key",
        runtime="openai_chat_completions",
    ),
}
LUNA = PROVIDERS["luna"]


def get_provider(key: str) -> Provider:
    if key not in PROVIDERS:
        raise ValueError(f"지원하지 않는 Cloud 모델: {key}; {list(PROVIDERS)}")
    return PROVIDERS[key]


def request_options(provider: Provider = LUNA) -> dict:
    if provider.api == "responses":
        return {
            "model": provider.model,
            "reasoning": {"effort": "max"},
            "max_output_tokens": 128000,
            "tools": [],
            "tool_choice": "none",
            "store": False,
            "service_tier": "default",
        }
    # Send only what the provider guide documents; the rest stays at provider defaults.
    return {"model": provider.model}


def build_request(provider: Provider, prompt: str) -> dict:
    field = "input" if provider.api == "responses" else "messages"
    return {**request_options(provider), field: [{"role": "user", "content": prompt}]}


def generation_config(provider: Provider) -> dict:
    config = {
        **request_options(provider),
        "temperature": None,
        "temperature_reason": "Not sent; provider default applies",
    }
    if provider.api == "chat_completions":
        config["max_tokens"] = None
        config["max_tokens_reason"] = "Not sent; provider default applies"
    return config


def create_client(provider: Provider = LUNA) -> OpenAI:
    key = os.environ.get(provider.env_var, "").strip()
    if not key:
        raise SystemExit(
            f"{provider.env_var} 환경변수가 없어 API를 호출하지 않았습니다."
        )
    return OpenAI(
        api_key=key,
        base_url=provider.base_url,
        timeout=TIMEOUT_SECONDS,
        max_retries=0,
    )


def send(client, provider: Provider, request: dict):
    if provider.api == "responses":
        return client.responses.create(**request)
    return client.chat.completions.create(**request)


def normalize(provider: Provider, response, data: dict) -> dict:
    """Map a provider reply onto one saved shape; the raw file is never rewritten."""
    if provider.api == "responses":
        return {
            "response_id": data.get("id"),
            "status": data.get("status"),
            "incomplete_details": data.get("incomplete_details"),
            "content": response.output_text or "",
            "service_tier": data.get("service_tier"),
        }
    choices = data.get("choices")
    # An empty or malformed choice list is a failed response, not a crash: raising here
    # would leave the reserved directory unusable and block the retry of a paid request.
    choice = choices[0] if isinstance(choices, list) and choices else None
    choice = choice if isinstance(choice, dict) else {}
    message = choice.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    reason = choice.get("finish_reason")
    return {
        "response_id": data.get("id"),
        "status": COMPLETION_STATUS.get(reason),
        "incomplete_details": {"reason": "max_output_tokens"}
        if reason == "length"
        else None,
        "content": content or "",
        "service_tier": data.get("service_tier"),
        "finish_reason": reason,
    }
