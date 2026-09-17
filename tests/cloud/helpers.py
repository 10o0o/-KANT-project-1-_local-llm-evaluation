def usage(inputs=1000, read=200, write=100, output=500):
    return {
        "input_tokens": inputs,
        "input_tokens_details": {"cached_tokens": read, "cache_write_tokens": write},
        "output_tokens": output,
        "output_tokens_details": {"reasoning_tokens": 400},
        "total_tokens": inputs + output,
    }


def chat_usage(prompt=1000, cached=200, completion=500):
    return {
        "prompt_tokens": prompt,
        "prompt_tokens_details": {"cached_tokens": cached},
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }
