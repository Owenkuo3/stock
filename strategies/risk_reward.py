from scoring.risk_reward_scoring import get_risk_grade, get_volatility_level
from utils import round_value


def analyze_risk_reward(base: dict, mode: str) -> dict:
    close = base["close"]
    ma20 = base["ma20"]
    ma60 = base["ma60"]
    recent_high = base["recent_high"]
    recent_low = base["recent_low"]
    atr14 = base["atr14"]
    atr_pct = base["atr_pct"]
    volume = base["volume"]
    volume_ma20 = base["volume_ma20"]
    distance_to_recent_high_pct = base["distance_to_recent_high_pct"]

    if close > ma20 > ma60:
        trend = "bullish"
    elif close > ma60 and ma20 <= ma60:
        trend = "neutral_bullish"
    elif close < ma60:
        trend = "weak"
    else:
        trend = "neutral"

    target_price = recent_high
    expected_return_pct = (target_price - close) / close * 100

    structure_stop_price = recent_low
    volatility_stop_price = close - 2 * atr14
    stop_loss_price = min(structure_stop_price, volatility_stop_price)

    expected_loss_pct = (close - stop_loss_price) / close * 100
    stop_atr_multiple = None if atr14 <= 0 else (close - stop_loss_price) / atr14

    volatility_level = get_volatility_level(atr_pct)

    if expected_loss_pct <= 0:
        risk_reward_ratio = None
    elif expected_return_pct <= 0:
        risk_reward_ratio = 0
    else:
        risk_reward_ratio = expected_return_pct / expected_loss_pct

    risk_grade = get_risk_grade(
        trend=trend,
        risk_reward_ratio=risk_reward_ratio,
        expected_loss_pct=expected_loss_pct,
        atr_pct=atr_pct,
        expected_return_pct=expected_return_pct,
        volatility_level=volatility_level,
    )

    def check_filter() -> bool:
        rr_ok = (risk_reward_ratio is not None) and (risk_reward_ratio >= {"loose": 1.5, "standard": 2, "strict": 3}[mode])

        if mode == "loose":
            return rr_ok and expected_loss_pct <= 10 and close > ma60
        if mode == "standard":
            return (
                rr_ok
                and expected_loss_pct <= 8
                and close > ma20
                and close > ma60
                and volume >= volume_ma20 * 0.8
                and volatility_level != "extreme"
            )
        return (
            rr_ok
            and expected_loss_pct <= 5
            and close > ma20
            and ma20 > ma60
            and volume >= volume_ma20
            and volatility_level in ["low", "medium"]
            and distance_to_recent_high_pct >= 2
        )

    passed_filter = check_filter()

    reasons = []
    if trend in ["bullish", "neutral_bullish"]:
        reasons.append("股價位於 MA20 與 MA60 之上，趨勢偏多")
    elif trend == "weak":
        reasons.append("股價低於 MA60，趨勢偏弱")
    else:
        reasons.append("趨勢中性，需等待更明確方向")

    rr_display = "None" if risk_reward_ratio is None else f"{round_value(risk_reward_ratio):.2f}"
    reasons.append(
        f"預估報酬率為 {round_value(expected_return_pct):.2f}%，預估虧損率為 {round_value(expected_loss_pct):.2f}%，風報比為 {rr_display}"
    )

    zh_vol_map = {"low": "低", "medium": "中等", "high": "高", "extreme": "極高"}
    reasons.append(f"ATR 波動率為 {round_value(atr_pct):.2f}%，屬於{zh_vol_map[volatility_level]}波動")

    if stop_atr_multiple is not None:
        reasons.append(f"停損距離約為 {round_value(stop_atr_multiple):.2f} 倍 ATR")
        if stop_atr_multiple < 1.5:
            reasons.append("停損距離小於 1.5 倍 ATR，容易被正常波動洗出場")
        if stop_atr_multiple > 3:
            reasons.append("停損距離大於 3 倍 ATR，代表進場位置可能不佳或虧損成本偏高")

    if volatility_level == "high":
        reasons.append("ATR 波動率偏高，需降低部位或提高風險控管")
    if volatility_level == "extreme":
        reasons.append("ATR 波動率極高，即使風報比看起來不錯，也不應視為低風險")
    if expected_return_pct <= 0:
        reasons.append("目前價格已接近或高於 lookback 區間高點，上方空間有限")

    reasons.append(f"{'符合' if passed_filter else '不符合'} {mode} 篩選條件")

    output = {
        **base,
        "trend": trend,
        "target_price": target_price,
        "structure_stop_price": structure_stop_price,
        "volatility_stop_price": volatility_stop_price,
        "stop_loss_price": stop_loss_price,
        "expected_return_pct": expected_return_pct,
        "expected_loss_pct": expected_loss_pct,
        "risk_reward_ratio": risk_reward_ratio,
        "stop_atr_multiple": stop_atr_multiple,
        "volatility_level": volatility_level,
        "risk_grade": risk_grade,
        "passed_filter": passed_filter,
        "reasons": reasons,
    }

    return output
