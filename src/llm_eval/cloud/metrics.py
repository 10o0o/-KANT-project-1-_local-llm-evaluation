from decimal import Decimal

from llm_eval.cloud.client import MODEL

PRICE_SOURCE = "https://developers.openai.com/api/docs/models/gpt-5.6-luna"
PRICE_CHECKED_AT = "2026-09-16"
RATES = {"input": "0.20", "cache_read": "0.02", "cache_write": "0.25", "output": "1.20"}


def token_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def estimated_cost(usage, response_model, service_tier):
    result = {
        "estimated_usd": None,
        "reason": None,
        "currency": "USD",
        "kind": "estimate_not_invoice",
        "rates_per_million_tokens": dict(RATES),
        "source": PRICE_SOURCE,
        "checked_at": PRICE_CHECKED_AT,
        "pricing_model": MODEL,
    }
    if response_model != MODEL or service_tier != "default":
        result["reason"] = "Response model or service tier does not match verified pricing"
        return result
    details = usage.get("input_tokens_details") or {}
    counts = {
        "input": usage.get("input_tokens"),
        "cache_read": details.get("cached_tokens"),
        "cache_write": details.get("cache_write_tokens"),
        "output": usage.get("output_tokens"),
    }
    if not all(token_count(v) for v in counts.values()):
        result["reason"] = "Missing or invalid input/output/cache token counts"
        return result
    if counts["input"] > 272000:
        result["reason"] = "Long-context pricing is outside this verified rate table"
        return result
    uncached = counts["input"] - counts["cache_read"] - counts["cache_write"]
    if uncached < 0:
        result["reason"] = "Cache token counts exceed total input tokens"
        return result
    billable = {**counts, "input": uncached}
    result["billable_tokens"] = billable
    amount = sum(Decimal(n) * Decimal(RATES[k]) for k, n in billable.items())
    result["estimated_usd"] = float(amount / Decimal(1_000_000))
    return result


def measured_metrics(elapsed, response):
    usage = response.get("usage") or {}
    inputs = usage.get("input_tokens_details") or {}
    outputs = usage.get("output_tokens_details") or {}
    result = {"response_elapsed_seconds": elapsed}
    for key, value in {
        "prompt_tokens": usage.get("input_tokens"),
        "completion_tokens": usage.get("output_tokens"),
        "reasoning_tokens": outputs.get("reasoning_tokens"),
        "cached_input_tokens": inputs.get("cached_tokens"),
        "cache_write_tokens": inputs.get("cache_write_tokens"),
    }.items():
        result[key] = value if token_count(value) else None
        result[f"{key}_reason"] = None if token_count(value) else "Usage unavailable or invalid"
    result.update(
        generation_tokens_per_second=None,
        generation_tokens_per_second_reason="Cloud API does not provide server generation duration",
        model_load_seconds=None,
        model_load_reason="Cloud API does not provide model load duration",
        memory={"value": None, "reason": "Cloud model VRAM is not exposed by the API"},
        cost=estimated_cost(usage, response.get("model"), response.get("service_tier")),
    )
    return result
