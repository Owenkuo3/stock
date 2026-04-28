from scoring.momentum_scoring import (
    calc_momentum_score,
    calc_risk_score,
    get_final_decision,
    get_momentum_grade,
    get_risk_level,
)
from utils import round_value


def analyze_momentum(base: dict, mode: str, row: dict) -> dict:
    close = base["close"]
    ma5, ma10, ma20, ma60 = base["ma5"], base["ma10"], base["ma20"], base["ma60"]
    recent_high = base["recent_high"]
    volume = base["volume"]
    volume_ma5 = base["volume_ma5"]
    volume_ma20 = base["volume_ma20"]
    return_5d_pct = base["return_5d_pct"]
    return_20d_pct = base["return_20d_pct"]
    atr_pct = base["atr_pct"]
    distance_to_recent_high_pct = base["distance_to_recent_high_pct"]

    volume_ratio = 0 if volume_ma20 <= 0 else volume / volume_ma20
    volume_ma5_ratio = 0 if volume_ma20 <= 0 else volume_ma5 / volume_ma20
    upper_shadow_pct = (row["High"] - max(row["Open"], row["Close"])) / row["Close"] * 100

    metrics = {
        **base,
        "volume_ratio": volume_ratio,
        "volume_ma5_ratio": volume_ma5_ratio,
        "upper_shadow_pct": upper_shadow_pct,
    }

    momentum_score = calc_momentum_score(metrics)
    momentum_grade = get_momentum_grade(momentum_score)
    risk_score = calc_risk_score(metrics)
    risk_level = get_risk_level(risk_score)
    final_decision = get_final_decision(momentum_grade, risk_level)

    if close > recent_high:
        breakout_status = "突破 lookback 區間高點"
    elif 0 <= distance_to_recent_high_pct <= 3:
        breakout_status = "接近 lookback 區間高點"
    else:
        breakout_status = "尚未接近突破"

    if volume_ratio >= 2:
        volume_status = f"成交量為 20 日均量 {round_value(volume_ratio):.2f} 倍，量能明顯放大"
    elif volume_ratio >= 1:
        volume_status = "成交量略高於 20 日均量"
    else:
        volume_status = "成交量不足"

    if close > ma5 > ma10 > ma20 > ma60:
        trend_status = "均線多頭排列"
    elif close > ma20 > ma60:
        trend_status = "股價位於 MA20 與 MA60 之上"
    else:
        trend_status = "股價跌破 MA20，短線轉弱" if close < ma20 else "均線結構中性"

    if return_5d_pct > 30:
        overheat_status = "短線漲幅過熱，不建議追高"
    elif return_5d_pct > 20:
        overheat_status = "近 5 日漲幅偏大，追高風險升高"
    else:
        overheat_status = "短線漲幅正常"

    def check_filter() -> bool:
        if mode == "loose":
            return momentum_score >= 55 and risk_score < 80 and close > ma20
        if mode == "standard":
            return momentum_score >= 65 and risk_score < 70 and close > ma20 and volume_ratio >= 1.2
        return (
            momentum_score >= 80
            and risk_score < 60
            and close > ma20
            and close > ma60
            and volume_ratio >= 1.5
            and risk_level in ["low", "medium"]
        )

    passed_filter = check_filter()

    reasons = [
        f"收盤價{breakout_status}，價格進入強勢區" if breakout_status != "尚未接近突破" else "尚未接近 lookback 區間高點，突破訊號未成形",
        volume_status,
        "MA5 > MA10 > MA20 > MA60，均線呈現多頭排列" if close > ma5 > ma10 > ma20 > ma60 else trend_status,
        f"近 5 日漲幅為 {round_value(return_5d_pct):.2f}%，具備短線動能但仍需注意追高風險",
        f"ATR 波動率為 {round_value(atr_pct):.2f}%，屬於{'高' if atr_pct >= 4 else '中低'}波動",
        f"動能分數為 {momentum_score}，風險分數為 {risk_score}",
        f"{'符合' if passed_filter else '不符合'} {mode} 篩選條件",
    ]

    if risk_level == "high":
        reasons.append("風險等級偏高，若要操作應降低部位並嚴格執行停損")
    if risk_level == "extreme":
        reasons.append("風險等級極高，即使動能強，也不建議追高")
    if close < ma20:
        reasons.append("股價跌破 MA20，短線動能結構轉弱")
    if volume_ratio < 1:
        reasons.append("成交量低於 20 日均量，動能確認不足")
    if upper_shadow_pct >= 3:
        reasons.append("當日上影線偏長，代表上方賣壓增加")

    return {
        **base,
        "momentum_score": momentum_score,
        "momentum_grade": momentum_grade,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "final_decision": final_decision,
        "volume_ratio": volume_ratio,
        "volume_ma5_ratio": volume_ma5_ratio,
        "upper_shadow_pct": upper_shadow_pct,
        "breakout_status": breakout_status,
        "volume_status": volume_status,
        "trend_status": trend_status,
        "overheat_status": overheat_status,
        "passed_filter": passed_filter,
        "reasons": reasons,
    }
