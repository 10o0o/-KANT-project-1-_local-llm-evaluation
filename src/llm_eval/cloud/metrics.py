from decimal import Decimal

from llm_eval.cloud.client import LUNA, Provider

PRICING = {
    "luna": {
        "source": "https://developers.openai.com/api/docs/models/gpt-5.6-luna",
        "checked_at": "2026-09-16",
        "rates": {
            "input": "0.20",
            "cache_read": "0.02",
            "cache_write": "0.25",
            "output": "1.20",
        },
        "max_input_tokens": 272000,
    }
}
USAGE_FIELDS = {
    "responses": {
        "prompt": "input_tokens",
        "completion": "output_tokens",
        "input_details": "input_tokens_details",
        "output_details": "output_tokens_details",
    },
    "chat_completions": {
        "prompt": "prompt_tokens",
        "completion": "completion_tokens",
        "input_details": "prompt_tokens_details",
        "output_details": "completion_tokens_details",
    },
}


def token_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def estimated_cost(usage, response_model, service_tier, provider: Provider = LUNA):
    pricing = PRICING.get(provider.key)
    result = {
        "estimated_usd": None,
        "reason": None,
        "currency": "USD",
        "kind": "estimate_not_invoice",
        "rates_per_million_tokens": dict(pricing["rates"]) if pricing else None,
        "source": pricing["source"] if pricing else None,
        "checked_at": pricing["checked_at"] if pricing else None,
        "pricing_model": provider.model if pricing else None,
    }
    # Without a verified public rate table an estimate would be invented, not measured.
    if pricing is None:
        result["reason"] = f"No verified public price table for {provider.model}"
        return result
    if response_model != provider.model or service_tier != "default":
        result["reason"] = (
            "Response model or service tier does not match verified pricing"
        )
        return result
    fields = USAGE_FIELDS[provider.api]
    rates = pricing["rates"]
    details = usage.get(fields["input_details"]) or {}
    counts = {
        "input": usage.get(fields["prompt"]),
        "cache_read": details.get("cached_tokens"),
        "cache_write": details.get("cache_write_tokens"),
        "output": usage.get(fields["completion"]),
    }
    if not all(token_count(v) for v in counts.values()):
        result["reason"] = "Missing or invalid input/output/cache token counts"
        return result
    if counts["input"] > pricing["max_input_tokens"]:
        result["reason"] = "Long-context pricing is outside this verified rate table"
        return result
    uncached = counts["input"] - counts["cache_read"] - counts["cache_write"]
    if uncached < 0:
        result["reason"] = "Cache token counts exceed total input tokens"
        return result
    billable = {**counts, "input": uncached}
    result["billable_tokens"] = billable
    amount = sum(Decimal(n) * Decimal(rates[k]) for k, n in billable.items())
    result["estimated_usd"] = float(amount / Decimal(1_000_000))
    return result


def measured_metrics(elapsed, response, provider: Provider = LUNA):
    fields = USAGE_FIELDS[provider.api]
    usage = response.get("usage") or {}
    inputs = usage.get(fields["input_details"]) or {}
    outputs = usage.get(fields["output_details"]) or {}
    result = {"response_elapsed_seconds": elapsed}
    for key, value in {
        "prompt_tokens": usage.get(fields["prompt"]),
        "completion_tokens": usage.get(fields["completion"]),
        "reasoning_tokens": outputs.get("reasoning_tokens"),
        "cached_input_tokens": inputs.get("cached_tokens"),
        "cache_write_tokens": inputs.get("cache_write_tokens"),
    }.items():
        result[key] = value if token_count(value) else None
        result[f"{key}_reason"] = (
            None if token_count(value) else "Usage unavailable or invalid"
        )
    result.update(
        generation_tokens_per_second=None,
        generation_tokens_per_second_reason="Cloud API does not provide server generation duration",
        model_load_seconds=None,
        model_load_reason="Cloud API does not provide model load duration",
        memory={"value": None, "reason": "Cloud model VRAM is not exposed by the API"},
        cost=estimated_cost(
            usage, response.get("model"), response.get("service_tier"), provider
        ),
    )
    return result
