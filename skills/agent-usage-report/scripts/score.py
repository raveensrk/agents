"""Scoring: a per-model intelligence composite and a cost-efficiency score.

Both scores are built only from the signals you chose, and both are relative:
a model's score is its position among the models you actually use, not an
absolute benchmark. That is deliberate - it answers "which of my models is
most efficient or most intelligent for the way I work".

Intelligence signals (all normalised to 0-100, best to worst):

    turns_per_request   fewer turns to close a request      (lower better)
    failure_rate        errored turns + failed tool calls   (lower better)
    reasoning_share     reasoning tokens per output token   (higher better)
    tokens_per_request  total tokens spent per request      (lower better)
    correction_rate     pushback per request                (lower better)

Efficiency is quality per dollar: intelligence divided by the blended cost per
million tokens. A capable free model wins; an expensive model has to earn it.
"""

from __future__ import annotations

DEFAULT_WEIGHTS = {
    "turns_per_request": 0.30,
    "failure_rate": 0.25,
    "reasoning_share": 0.20,
    "tokens_per_request": 0.15,
    "correction_rate": 0.10,
}

_LOWER_IS_BETTER = {
    "turns_per_request": True,
    "failure_rate": True,
    "reasoning_share": False,
    "tokens_per_request": True,
    "correction_rate": True,
}


def _rank_scores(values, lower_better):
    """Percentile scores from ranks, so outliers cannot compress the field.

    Ties share a score. The best model gets 100 and the worst gets 0; with a
    single model (or all ties) everyone gets 50.
    """
    count = len(values)
    if count <= 1:
        return [50.0] * count
    order = sorted(range(count), key=lambda index: values[index])
    ranks = [0.0] * count
    index = 0
    while index < count:
        end = index
        while end + 1 < count and values[order[end + 1]] == values[order[index]]:
            end += 1
        average = (index + end) / 2.0
        for position in range(index, end + 1):
            ranks[order[position]] = average
        index = end + 1
    scores = []
    for rank in ranks:
        fraction = rank / float(count - 1)
        scores.append(round((1.0 - fraction) * 100.0 if lower_better else fraction * 100.0, 1))
    return scores


def compute(dataset, config=None):
    config = config or {}
    settings = config.get("score") or {}
    weights = dict(DEFAULT_WEIGHTS)
    weights.update(settings.get("weights") or {})
    min_turns = int(settings.get("min_turns", 30))
    min_turns = int(config.get("min_turns", min_turns))

    models = dataset["models"]
    for entry in models.values():
        entry["failure_rate"] = round(
            (entry.get("error_stops", 0) + entry.get("tool_errors", 0)) * 100.0
            / (entry.get("turns") or 1),
            2,
        )
        entry["cost_per_turn"] = round(
            (entry.get("cost_total") or 0.0) / (entry.get("turns") or 1), 6)
        entry["waste_cost"] = round(entry["cost_per_turn"] * entry.get("error_stops", 0), 6)
        entry["avg_input_per_turn"] = int(
            (entry.get("input") or 0) / (entry.get("turns") or 1))
        window = entry.get("context_window") or 0
        entry["context_pressure"] = round(
            entry["avg_input_per_turn"] * 100.0 / window, 2) if window else 0.0

    ranked = [e for e in models.values() if e["turns"] >= min_turns]
    unranked = [e for e in models.values() if e["turns"] < min_turns]
    shrink = float(settings.get("shrink_turns", config.get("shrink_turns", 200)))
    dataset["shrink_turns"] = shrink

    if ranked:
        for signal in DEFAULT_WEIGHTS:
            values = [e.get(signal, 0) or 0 for e in ranked]
            scores = _rank_scores(values, _LOWER_IS_BETTER[signal])
            for entry, score in zip(ranked, scores):
                entry.setdefault("signals", {})[signal] = score
        for entry in ranked:
            total = 0.0
            for signal, weight in weights.items():
                total += entry["signals"].get(signal, 0) * weight
            entry["intelligence_raw"] = round(total, 1)

        # Shrink small samples toward the mean so a model with barely enough
        # turns cannot out-rank one with thousands on a lucky percentile.
        mean = sum(e["intelligence_raw"] for e in ranked) / float(len(ranked))
        for entry in ranked:
            turns = float(entry["turns"])
            if shrink > 0:
                adjusted = (turns * entry["intelligence_raw"] + shrink * mean) / (turns + shrink)
            else:
                adjusted = entry["intelligence_raw"]
            entry["intelligence_score"] = round(adjusted, 1)
            entry["intelligence_shrink"] = round(entry["intelligence_raw"] - adjusted, 1)

        # Efficiency: quality bought per dollar, floored to keep free models finite.
        for entry in ranked:
            cost = entry.get("cost_per_million") or 0.0
            floor = 0.01
            entry["value_per_dollar"] = round(
                entry["intelligence_score"] / (cost + floor), 3)
        values = [e["value_per_dollar"] for e in ranked]
        scores = _rank_scores(values, lower_better=False)
        for entry, score in zip(ranked, scores):
            entry["efficiency_score"] = score

        order = sorted(ranked, key=lambda e: (-e["intelligence_score"], e["model"]))
        efficiency_order = sorted(
            ranked, key=lambda e: (-e["efficiency_score"], e["model"]))
        for index, entry in enumerate(order, 1):
            entry["intelligence_rank"] = index
        for index, entry in enumerate(efficiency_order, 1):
            entry["efficiency_rank"] = index

    for entry in unranked:
        entry["intelligence_score"] = None
        entry["intelligence_raw"] = None
        entry["efficiency_score"] = None
        entry["intelligence_rank"] = None
        entry["efficiency_rank"] = None
        entry["confidence"] = "low"
    for entry in ranked:
        entry["confidence"] = "high" if entry["turns"] >= 100 else "medium"

    leaders = {
        "most_intelligent": ranked and max(
            ranked, key=lambda e: e["intelligence_score"]) or None,
        "most_efficient": ranked and max(
            ranked, key=lambda e: e["efficiency_score"]) or None,
        "cheapest": None,
        "biggest_spend": None,
    }
    with_cost = [e for e in models.values() if e.get("cost_per_million")]
    if with_cost:
        leaders["cheapest"] = min(with_cost, key=lambda e: e["cost_per_million"])
    spenders = [e for e in models.values() if (e.get("cost_total") or 0) > 0]
    if spenders:
        leaders["biggest_spend"] = max(spenders, key=lambda e: e["cost_total"])

    dataset["ranking"] = ranked
    dataset["unranked"] = unranked
    dataset["leaders"] = leaders
    dataset["min_turns"] = min_turns
    dataset["weights"] = weights
    dataset["totals"] = _totals(dataset, models)
    return dataset


def _totals(dataset, models):
    total_tokens = sum(e["total"] for e in models.values())
    cached = sum(e["cache_read"] + e["cache_write"] for e in models.values())
    cost = sum(e.get("cost_total") or 0.0 for e in models.values())
    recorded = sum(e.get("cost_recorded") or 0.0 for e in models.values())
    uncached = sum(e["input"] for e in models.values())
    output = sum(e["output"] for e in models.values())
    reasoning = sum(e["reasoning"] for e in models.values())
    cache_saving = _cache_saving(models)
    split = _cost_split(models)
    return {
        "tokens": total_tokens,
        "input": uncached,
        "output": output,
        "cache_read": sum(e["cache_read"] for e in models.values()),
        "cache_write": sum(e["cache_write"] for e in models.values()),
        "cached": cached,
        "reasoning": reasoning,
        "cost": cost,
        "cost_recorded": recorded,
        "cost_computed": cost - recorded,
        "cost_split": split,
        "cache_saving": cache_saving,
        "cache_hit_rate": round(
            sum(e["cache_read"] for e in models.values()) * 100.0
            / ((uncached + sum(e["cache_read"] for e in models.values())) or 1), 1),
        "models": len(models),
        "sessions": dataset["sessions"],
        "requests": dataset["requests"],
        "turns": dataset["turns"],
        "waste": round(sum(e.get("waste_cost") or 0.0 for e in models.values()), 4),
        "wasted_turns": sum(e.get("error_stops", 0) for e in models.values()),
        "blended_per_million": round(cost / total_tokens * 1_000_000, 4) if total_tokens else 0.0,
    }


def _cost_split(models):
    """Where the money went, estimated from rates for every model with pricing."""
    split = {"input": 0.0, "cache_read": 0.0, "cache_write": 0.0, "output": 0.0}
    for entry in models.values():
        rates = entry.get("rates")
        if not rates:
            continue
        for key in split:
            rate = rates.get(key)
            if rate is None:
                continue
            split[key] += float(entry.get(key) or 0) * float(rate) / 1_000_000.0
    return {k: round(v, 4) for k, v in split.items()}


def _cache_saving(models):
    """Dollars saved by reading from cache instead of paying full input rate."""
    saving = 0.0
    for entry in models.values():
        rates = entry.get("rates")
        if not rates:
            continue
        full = rates.get("input")
        discounted = rates.get("cache_read")
        if full is None or discounted is None:
            continue
        reads = entry["cache_read"]
        if entry.get("cache_read_rec"):
            reads = entry["cache_read"]  # recorded cost already reflects the discount
        saving += reads * max(0.0, float(full) - float(discounted)) / 1_000_000.0
    return round(saving, 4)
