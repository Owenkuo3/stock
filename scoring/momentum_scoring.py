def calc_momentum_score(metrics: dict) -> int:
    score = 0

    close = metrics["close"]
    recent_high = metrics["recent_high"]
    distance_to_recent_high_pct = metrics["distance_to_recent_high_pct"]
    volume_ratio = metrics["volume_ratio"]
    volume_ma5_ratio = metrics["volume_ma5_ratio"]
    ma5, ma10, ma20, ma60 = metrics["ma5"], metrics["ma10"], metrics["ma20"], metrics["ma60"]
    return_5d_pct = metrics["return_5d_pct"]
    return_20d_pct = metrics["return_20d_pct"]
    atr_pct = metrics["atr_pct"]

    if close > recent_high:
        score += 25
    elif 0 <= distance_to_recent_high_pct <= 3:
        score += 10

    if volume_ratio >= 2:
        score += 20
    elif volume_ratio >= 1.5:
        score += 12
    elif volume_ratio >= 1.0:
        score += 5

    if volume_ma5_ratio >= 1.5:
        score += 10
    elif volume_ma5_ratio >= 1.2:
        score += 5

    if close > ma5 > ma10 > ma20 > ma60:
        score += 20
    elif close > ma20 > ma60:
        score += 10

    if 8 <= return_5d_pct <= 20:
        score += 10
    elif 3 <= return_5d_pct < 8:
        score += 5

    if 15 <= return_20d_pct <= 40:
        score += 10
    elif 8 <= return_20d_pct < 15:
        score += 5

    if close > ma20 and close > ma60:
        score += 5

    if return_5d_pct > 30:
        score -= 15
    if return_20d_pct > 60:
        score -= 15

    if atr_pct > 8:
        score -= 10
    if atr_pct > 12:
        score -= 10

    if close < ma20:
        score = min(score, 49)
    if volume_ratio < 0.8:
        score = min(score, 59)

    return max(0, min(100, int(round(score))))


def get_momentum_grade(momentum_score: int) -> str:
    if momentum_score >= 80:
        return "A"
    if momentum_score >= 65:
        return "B"
    if momentum_score >= 50:
        return "C"
    if momentum_score >= 35:
        return "D"
    return "E"


def calc_risk_score(metrics: dict) -> int:
    risk = 0

    atr_pct = metrics["atr_pct"]
    distance_to_ma20_pct = metrics["distance_to_ma20_pct"]
    return_5d_pct = metrics["return_5d_pct"]
    return_20d_pct = metrics["return_20d_pct"]
    close = metrics["close"]
    recent_high = metrics["recent_high"]
    distance_to_recent_high_pct = metrics["distance_to_recent_high_pct"]
    volume_ratio = metrics["volume_ratio"]
    upper_shadow_pct = metrics["upper_shadow_pct"]
    volume_ma20 = metrics["volume_ma20"]

    if atr_pct < 2:
        risk += 5
    elif atr_pct < 4:
        risk += 15
    elif atr_pct < 6:
        risk += 30
    elif atr_pct < 8:
        risk += 45
    else:
        risk += 60

    if distance_to_ma20_pct > 20:
        risk += 30
    elif distance_to_ma20_pct > 12:
        risk += 20
    elif distance_to_ma20_pct > 6:
        risk += 10

    if return_5d_pct > 30:
        risk += 30
    elif return_5d_pct > 20:
        risk += 20
    elif return_5d_pct > 12:
        risk += 10

    if return_20d_pct > 60:
        risk += 25
    elif return_20d_pct > 40:
        risk += 15

    if close > recent_high and volume_ratio < 1.5:
        risk += 25
    elif 0 <= distance_to_recent_high_pct <= 3 and volume_ratio < 1:
        risk += 15

    if upper_shadow_pct >= 5:
        risk += 20
    elif upper_shadow_pct >= 3:
        risk += 10

    if volume_ma20 < 100000:
        risk += 40
    elif volume_ma20 < 500000:
        risk += 20

    return max(0, min(100, int(round(risk))))


def get_risk_level(risk_score: int) -> str:
    if risk_score < 30:
        return "low"
    if risk_score < 60:
        return "medium"
    if risk_score < 80:
        return "high"
    return "extreme"


def get_final_decision(momentum_grade: str, risk_level: str) -> str:
    if momentum_grade == "A" and risk_level in ["low", "medium"]:
        return "強勢動能，風險尚可控，可列入觀察"
    if momentum_grade == "A" and risk_level == "high":
        return "動能很強，但追高與波動風險偏高，只適合小部位或等待拉回"
    if momentum_grade == "A" and risk_level == "extreme":
        return "動能很強，但風險過高，不建議追高"
    if momentum_grade == "B" and risk_level in ["low", "medium"]:
        return "偏強觀察，尚未完全加速"
    if momentum_grade == "B" and risk_level in ["high", "extreme"]:
        return "有動能，但風險偏高，等待更好的進場位置"
    if momentum_grade == "C":
        return "有部分動能，但訊號不明確"
    return "動能不足，不符合飆股條件"
