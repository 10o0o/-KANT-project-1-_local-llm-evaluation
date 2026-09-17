from openai import OpenAI

from llm_eval.shared.workloads import workload

REASONING_BUDGET_MESSAGE = (
    "Considering the limited time by the user, "
    "I have to give the solution based on the thinking directly now."
)
TEMPERATURE = 0
MAX_TOKENS = 61440
REASONING_BUDGET_TOKENS = 53248
WARMUP_PROMPT = "워밍업 요청입니다. 최종 답변으로 WARMUP_OK라고만 답하세요."
WARMUP_TEMPERATURE = 0
WARMUP_MAX_TOKENS = 128
WARMUP_REASONING_BUDGET_TOKENS = 64


def create_client(base_url: str = "http://127.0.0.1:8080/v1"):
    return OpenAI(
        base_url=base_url,
        api_key="local",
        timeout=3600.0,
        max_retries=0,
    )


def generation_config():
    return {
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "reasoning_budget_tokens": REASONING_BUDGET_TOKENS,
        "cache_prompt": False,
        "reasoning_budget_message": REASONING_BUDGET_MESSAGE,
    }


def chat(
    client: OpenAI,
    model: str,
    prompt: str,
    *,
    temperature: float = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
    reasoning_budget_tokens: int = REASONING_BUDGET_TOKENS,
    cache_prompt: bool = False,
    reasoning_budget_message: str = REASONING_BUDGET_MESSAGE,
):
    return client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={
            "reasoning_budget_tokens": reasoning_budget_tokens,
            "cache_prompt": cache_prompt,
            "reasoning_budget_message": reasoning_budget_message,
        },
    )


def request_warmup(client: OpenAI, model: str):
    return chat(
        client,
        model,
        WARMUP_PROMPT,
        temperature=WARMUP_TEMPERATURE,
        max_tokens=WARMUP_MAX_TOKENS,
        reasoning_budget_tokens=WARMUP_REASONING_BUDGET_TOKENS,
    )


def run_warmup(project_root, model: str):
    if model not in {"qwen36", "gemma4"}:
        raise ValueError(f"지원하지 않는 로컬 모델: {model}")
    with workload(project_root, "warmup", allow_inherited=True):
        with create_client() as client:
            response = request_warmup(client, model)
    print(f"워밍업 호출 완료: {model}")
    return response
