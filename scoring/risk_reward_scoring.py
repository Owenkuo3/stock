def get_volatility_level(atr_pct: float) -> str:
    if atr_pct < 2:
        return "low"
    if atr_pct < 4:
        return "medium"
    if atr_pct < 6:
        return "high"
    return "extreme"


def get_risk_grade(
    trend: str,
    risk_reward_ratio: float | None,
    expected_loss_pct: float,
    atr_pct: float,
    expected_return_pct: float,
    volatility_level: str,
) -> str:
    if trend == "weak" or expected_loss_pct > 10 or atr_pct >= 8 or expected_return_pct <= 0:
        return "E"

    rr = risk_reward_ratio if risk_reward_ratio is not None else -1

    if rr >= 3 and trend == "bullish" and expected_loss_pct <= 5:
        grade = "A"
    elif rr >= 2 and trend in ["bullish", "neutral_bullish"] and expected_loss_pct <= 8:
        grade = "B"
    elif rr >= 1.2:
        grade = "C"
    else:
        grade = "D"

    if volatility_level == "extreme" and grade in ["A", "B"]:
        grade = "C"

    return grade
