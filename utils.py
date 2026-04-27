import json
from datetime import datetime
from typing import Any


ALLOWED_LOOKBACKS = {20, 60, 120, 240}
ALLOWED_MODES = {"loose", "standard", "strict"}
ALLOWED_STRATEGIES = {"risk_reward", "momentum"}


def round_value(value: Any, digits: int = 2):
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return value


def error_json(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def parse_analysis_date(date_str: str | None):
    if date_str is None:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("analysis_date 格式錯誤，需為 YYYY-MM-DD") from exc
