import json
from datetime import datetime
from pathlib import Path
from time import perf_counter

from ollama import Client

project_root = Path(__file__).resolve().parents[2]
run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
result_dir = project_root / "results" / run_id
result_dir.mkdir(parents=True, exist_ok=False)

MODEL = [
    ("qwen36-35b-lowvram:latest", "qwen36"),
    ("gemma4:26b-a4b-it-q4_K_M", "gemma4"),
]
QUESTION = "프롬프트 엔지니어링이 무엇인지 초보자에게 두 문장으로 설명해 주세요."

# 내 PC에서 실행 중인 Ollama에 연결합니다.
client = Client(host="http://127.0.0.1:11434", timeout=180)

for model, name in MODEL:
    print(f"[{name}] 모델 워밍업 호출 시작")
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": "hi"}],
        stream=False,
        keep_alive="10m",
        options={"temperature": 0, "num_predict": 1024, "num_ctx": 4096},
    )
    print(f"[{name}] 워밍업 호출 완료")

    print(f"[{name}] 타이머 시작")
    start = perf_counter()

    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": QUESTION}],
        stream=False,
        keep_alive="10m",
        options={"temperature": 0, "num_predict": 1024, "num_ctx": 4096},
    )

    elapsed = perf_counter() - start

    print(f"\n[{name}] 답변")
    print(response.message.content)

    print(f"[{name}] 전체 응답 시간: {elapsed:.2f}초")

    output_path = result_dir / f"response_{name}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        response_JSON = response.model_dump_json(indent=2)
        f.write(response_JSON)

    with open(output_path, "r", encoding="utf-8") as f:
        saved_response = json.load(f)

    print(f"[{name}] 답변 저장 완료")
    print(saved_response["message"]["content"])

    client.generate(model=model, prompt="", keep_alive=0)
    print(f"[{name}] 모델 off")
