def get_path(payload: dict, path: str):
    value = payload
    for part in (path or "").split("."):
        if not part:
            continue
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def evaluate_operator(actual, operator: str, expected) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "gte":
        return actual is not None and actual >= expected
    if operator == "lte":
        return actual is not None and actual <= expected
    if operator == "gt":
        return actual is not None and actual > expected
    if operator == "lt":
        return actual is not None and actual < expected
    if operator == "contains":
        return actual is not None and str(expected).lower() in str(actual).lower()
    if operator == "in":
        return actual in (expected or [])
    return False


def has_automation_loop(payload: dict) -> bool:
    source = payload.get("source") or payload.get("metadata", {}).get("source")
    depth = int(
        payload.get("automation_depth") or payload.get("metadata", {}).get("automation_depth") or 0
    )
    return source == "automation" and depth >= 1
