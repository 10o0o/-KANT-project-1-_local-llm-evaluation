from openai import OpenAI


def create_client(base_url: str = "http://127.0.0.1:8080/v1"):
    return OpenAI(
        base_url=base_url,
        api_key="local",
        timeout=3600.0,
        max_retries=0,
    )


def chat(
    client: OpenAI,
    model: str,
    prompt: str,
    *,
    temperature: float = 0,
    max_tokens: int = 12288,
    reasoning_budget_tokens: int = 6144,
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
            "cache_prompt": False,
            "reasoning_budget_message": (
                "Considering the limited time by the user, "
                "I have to give the solution based on the thinking directly now."
            ),
        },
    )
