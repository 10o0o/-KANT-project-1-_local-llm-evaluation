from llm_eval.local.client import chat

WARMUP_PROMPT = "워밍업 요청입니다. 최종 답변으로 WARMUP_OK라고만 답하세요."
WARMUP_TEMPERATURE = 0
WARMUP_MAX_TOKENS = 128
WARMUP_REASONING_BUDGET_TOKENS = 64


def run_warmup(model: str, client):
    response = chat(
        client,
        model,
        WARMUP_PROMPT,
        temperature=WARMUP_TEMPERATURE,
        max_tokens=WARMUP_MAX_TOKENS,
        reasoning_budget_tokens=WARMUP_REASONING_BUDGET_TOKENS,
    )
    print(f"워밍업 호출 완료: {model}")
    return response
