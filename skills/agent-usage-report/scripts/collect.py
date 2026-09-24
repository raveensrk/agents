"""Turn collection: read every adapter, segment by user request, aggregate.

The unit of analysis is one assistant turn. A *request* is a human message plus
every assistant turn that follows it until the next human message. Requests are
the denominator for turns-per-request and corrections-per-request, which keeps
models comparable even when they are used very differently.
"""

from __future__ import annotations

import datetime
import re

from adapters import all_adapters

# A short user message that pushes back on the previous answer. Deliberately
# conservative: only messages after the first one and under 600 chars count.
_CORRECTION = re.compile(
    r"(?i)(?:^|\b)(no,|nope|not what|that'?s wrong|that'?s not|incorrect|"
    r"actually,|instead|don'?t |didn'?t |stop |revert|undo|try again|"
    r"still (?:not|fails|broken)|you (?:missed|forgot|should|need)|redo|fix that)"
)

_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def load(config=None):
    """Read every available adapter; return (records, detected, missing)."""
    records = []
    detected = []
    missing = []
    for adapter in all_adapters(config):
        label = getattr(adapter, "LABEL", getattr(adapter, "NAME", "?"))
        if not adapter.available():
            if not getattr(adapter, "OPTIONAL", False):
                missing.append(label)
            continue
        try:
            generated = list(adapter.records())
        except Exception:
            missing.append(label)
            continue
        detected.append({"name": getattr(adapter, "NAME", "?"), "label": label,
                         "records": len(generated)})
        records.extend(generated)
    return records, detected, missing


def _in_window(timestamp, since, until):
    if since is not None and timestamp < since:
        return False
    if until is not None and timestamp > until:
        return False
    return True


def _blank_model(model):
    return {
        "model": model,
        "providers": {},
        "harnesses": {},
        "turns": 0,
        "requests": 0,
        "corrections": 0,
        "input": 0,
        "cache_read": 0,
        "cache_write": 0,
        "output": 0,
        "reasoning": 0,
        "total": 0,
        "tool_calls": 0,
        "tool_errors": 0,
        "error_stops": 0,
        "cost_recorded": 0.0,
        "cost_computed": None,
        "tokens_recorded": 0,
        "input_rec": 0,
        "cache_read_rec": 0,
        "cache_write_rec": 0,
        "output_rec": 0,
        "context_window": 0,
        "thinking_levels": {},
        "tools": {},
        "first": None,
        "last": None,
        "cost_sources": {},
    }


def _bump(mapping, key, amount=1):
    mapping[key] = mapping.get(key, 0) + amount


def _as_int(value):
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def aggregate(records, since=None, until=None):
    """Segment records into requests and aggregate per model and per project."""
    records = [r for r in records if _in_window(r.get("timestamp") or 0, since, until)]
    records.sort(key=lambda r: (r.get("timestamp") or 0))

    sessions = {}
    for rec in records:
        key = (rec.get("harness"), rec.get("session_id"))
        sessions.setdefault(key, []).append(rec)

    models = {}
    projects = {}
    daily = {}
    switches = {}
    hourly = [[0] * 24 for _ in range(7)]
    sessions_seen = set()
    total_requests = 0
    total_turns = 0

    for (harness, session_id), items in sessions.items():
        sessions_seen.add((harness, session_id))
        request_index = -1
        segment_models = []
        first_user_seen = False
        previous_model = None

        for rec in items:
            project = rec.get("project") or harness
            if rec.get("kind") == "user":
                text = (rec.get("text") or "").strip()
                is_correction = False
                if first_user_seen and 0 < len(text) <= 600 and _CORRECTION.search(text):
                    is_correction = True
                first_user_seen = True
                if is_correction:
                    for model in set(segment_models):
                        models[model]["corrections"] += 1
                request_index += 1
                total_requests += 1
                segment_models = []
                continue

            model_key = rec.get("model") or "unknown"
            if model_key.startswith("<"):
                # Claude Code emits <synthetic> turns for context/limit errors.
                continue
            entry = models.get(model_key)
            if entry is None:
                entry = _blank_model(model_key)
                models[model_key] = entry

            entry["turns"] += 1
            total_turns += 1
            _bump(entry["providers"], rec.get("provider") or "unknown")
            _bump(entry["harnesses"], harness or "unknown")
            if rec.get("thinking_level"):
                _bump(entry["thinking_levels"], str(rec["thinking_level"]))
            if rec.get("context_window"):
                entry["context_window"] = max(
                    entry["context_window"], _as_int(rec["context_window"]))
            entry.setdefault("_request_keys", set()).add(
                (harness, session_id, request_index))

            for field in ("input", "cache_read", "cache_write", "output", "reasoning", "total"):
                entry[field] += int(rec.get(field) or 0)
            entry["tool_calls"] += int(rec.get("tool_calls") or 0)
            entry["tool_errors"] += int(rec.get("tool_errors") or 0)
            for tool_name, count in (rec.get("tools") or {}).items():
                _bump(entry["tools"], tool_name, int(count))
            if rec.get("stop_reason") in ("error", "aborted"):
                entry["error_stops"] += 1

            if previous_model is not None and previous_model != model_key:
                _bump(switches, (previous_model, model_key))
            previous_model = model_key

            cost = rec.get("cost")
            if cost is not None:
                entry["cost_recorded"] += float(cost)
                entry["cost_sources"][rec.get("cost_source") or "recorded"] = \
                    entry["cost_sources"].get(rec.get("cost_source") or "recorded", 0) + 1
                entry["tokens_recorded"] += int(rec.get("total") or 0)
                for field in ("input", "cache_read", "cache_write", "output"):
                    entry[field + "_rec"] += int(rec.get(field) or 0)

            ts = rec.get("timestamp") or 0
            if ts:
                if entry["first"] is None or ts < entry["first"]:
                    entry["first"] = ts
                if entry["last"] is None or ts > entry["last"]:
                    entry["last"] = ts

            segment_models.append(model_key)

            # Project rollup
            proj = projects.setdefault(project, {"project": project, "total": 0,
                                                 "cost_recorded": 0.0, "turns": 0,
                                                 "models": {}})
            proj["total"] += int(rec.get("total") or 0)
            proj["turns"] += 1
            if cost is not None:
                proj["cost_recorded"] += float(cost)
            _bump(proj["models"], model_key)

            # Time series
            dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc) if ts else None
            if dt is not None:
                day = dt.strftime("%Y-%m-%d")
                bucket = daily.setdefault(day, {"day": day, "total": 0, "cost_recorded": 0.0,
                                                "turns": 0, "models": {}})
                bucket["total"] += int(rec.get("total") or 0)
                bucket["turns"] += 1
                if cost is not None:
                    bucket["cost_recorded"] += float(cost)
                _bump(bucket["models"], model_key)
                local = dt.astimezone()
                hourly[local.weekday()][local.hour] += 1

    for entry in models.values():
        entry["requests"] = len(entry.pop("_request_keys", set()))
        total = entry["total"] or 1
        entry["cache_share"] = round(
            (entry["cache_read"] + entry["cache_write"]) * 100.0 / total, 1)
        # Bounded share: reasoning tokens are billed separately from output in
        # pi, Codex and Claude Code, so reasoning/output could exceed 100%.
        entry["reasoning_share"] = round(
            entry["reasoning"] * 100.0 / ((entry["reasoning"] + entry["output"]) or 1), 1)
        entry["tool_error_rate"] = round(
            entry["tool_errors"] * 100.0 / (entry["tool_calls"] or 1), 2)
        entry["error_rate"] = round(entry["error_stops"] * 100.0 / (entry["turns"] or 1), 2)
        entry["correction_rate"] = round(
            entry["corrections"] * 100.0 / (entry["requests"] or 1), 2)
        entry["turns_per_request"] = round(entry["turns"] / (entry["requests"] or 1), 2)
        entry["tokens_per_request"] = int(entry["total"] / (entry["requests"] or 1))

    return {
        "models": models,
        "projects": projects,
        "daily": daily,
        "switches": switches,
        "hourly": hourly,
        "weekdays": list(_WEEKDAYS),
        "sessions": len(sessions_seen),
        "requests": total_requests,
        "turns": total_turns,
    }
