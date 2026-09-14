from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="not-needed",
    timeout=180,
    max_retries=0,
)

MODEL = "sha256-34189c1048e57b9b0025058114185ce4dc37d045596666b67e377ef1f08398c0"
QUESTION = "프롬프트 엔지니어링이 무엇인지 초보자에게 두 문장으로 설명해 주세요."

response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": QUESTION}],
    temperature=0.5,
    max_tokens=1024,
    stream=False,
    # extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)

print("\n[Hyperclova_chat 답변]")
print(response.choices[0].message.content)

print("\n[디버깅]]")
print(response.model_dump_json(indent=2))
