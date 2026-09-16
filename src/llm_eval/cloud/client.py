import os

from openai import OpenAI

MODEL = "gpt-5.6-luna"
TIMEOUT_SECONDS = 3600


def request_options():
    return {
        "model": MODEL,
        "reasoning": {"effort": "max"},
        "max_output_tokens": 128000,
        "tools": [],
        "tool_choice": "none",
        "store": False,
        "service_tier": "default",
    }


def create_client():
    key = os.environ.get("openai_secret_key", "").strip()
    if not key:
        raise SystemExit("openai_secret_key 환경변수가 없어 API를 호출하지 않았습니다.")
    return OpenAI(
        api_key=key,
        base_url="https://api.openai.com/v1",
        timeout=TIMEOUT_SECONDS,
        max_retries=0,
    )
