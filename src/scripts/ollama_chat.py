import json

from ollama import Client

MODEL = "qwen36-35b-lowvram:latest"
QUESTION = "프롬프트 엔지니어링이 무엇인지 초보자에게 두 문장으로 설명해 주세요."

# 내 PC에서 실행 중인 Ollama에 연결합니다.
client = Client(host="http://127.0.0.1:11434", timeout=180)
print("Ollama에 질문을 보냈습니다. 답변을 기다려 주세요.")
response = client.chat(
    model=MODEL,
    messages=[{"role": "user", "content": QUESTION}],
    stream=False,
    options={"temperature": 0, "num_predict": 1024},
)

print("\n[Ollama 답변]")
print(response.message.content)


with open("response_qwen36.json", "w", encoding="utf-8") as f:
    response_JSON = response.model_dump_json(indent=2)
    f.write(response_JSON)

with open("response_qwen36.json", "r", encoding="utf-8") as f:
    saved_response = json.load(f)

print("\n[저장된 답변]")
print(saved_response["message"]["content"])
