from openai import OpenAI

def main():
    client = OpenAI(
        base_url="http://127.0.0.1:8080/v1",
        api_key="local",
        timeout=3600,
        max_retries=0,
    )

    r = client.chat.completions.create(
        # model="qwen36",
        model="gemma4",
        messages=[
            {
                "role": "user",
                "content": """
    다음 문제를 Python으로 해결하는 방법을 충분히 자세히 설명하세요.

    정수 n이 주어질 때 1부터 n까지의 합을 출력하세요.
    입력: 1000000
    """,
            }
        ],
        temperature=0,
        max_tokens=1024,
        extra_body={
            "reasoning_budget_tokens": 512,
        },
    )

    print(r.choices[0].message.content)
    print()
    print(r.model_dump().get("timings"))


if __name__ == "__main__":
    main()
