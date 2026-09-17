import re


def extract_python_code(response_text: str) -> str | None:
    python_blocks = re.findall(
        r"```python\s*(.*?)```",
        response_text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if len(python_blocks) == 1:
        return python_blocks[0].strip()

    if len(python_blocks) > 1:
        return python_blocks[-1].strip()

    generic_blocks = re.findall(
        r"```\s*(.*?)```",
        response_text,
        flags=re.DOTALL,
    )

    if generic_blocks:
        return generic_blocks[-1].strip()

    return None


# if __name__ == "__main__":
#     response = """
# 설명입니다.

# ```python
# n = int(input())
# print(n)
# ```

# 시간복잡도는 O(1)입니다.
# """

#     code = extract_python_code(response)

#     print(code)
