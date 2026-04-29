import pandas as pd

from scoring.risk_reward_scoring import get_risk_grade, get_volatility_level
from utils import TRADE_HORIZON_CONFIG, round_value


def _calc_loss_pct(close: float, stop_price: float) -> float:
    return (close - stop_price) / close * 100


def _calc_stop_atr_multiple(close: float, stop_price: float, atr14: float) -> float | None:
    if atr14 <= 0:
        return None
    return (close - stop_price) / atr14


def _calc_rr(expected_return_pct: float, expected_loss_pct: float) -> float | None:
    if expected_loss_pct <= 0:
        return None
    if expected_return_pct <= 0:
        return 0
    return expected_return_pct / expected_loss_pct


def _select_hybrid_stop(close: float, atr14: float, expected_return_pct: float, structure_stop_price: float, volatility_stop_price: float):
    structure_expected_loss_pct = _calc_loss_pct(close, structure_stop_price)
    volatility_expected_loss_pct = _calc_loss_pct(close, volatility_stop_price)

    structure_stop_atr_multiple = _calc_stop_atr_multiple(close, structure_stop_price, atr14)
    volatility_stop_atr_multiple = _calc_stop_atr_multiple(close, volatility_stop_price, atr14)

    structure_rr = _calc_rr(expected_return_pct, structure_expected_loss_pct)
    volatility_rr = _calc_rr(expected_return_pct, volatility_expected_loss_pct)

    structure_valid = structure_stop_atr_multiple is not None and structure_stop_atr_multiple >= 1.5
    volatility_valid = volatility_stop_atr_multiple is not None and volatility_stop_atr_multiple >= 1.5

    if structure_valid and volatility_valid:
        if structure_expected_loss_pct <= volatility_expected_loss_pct:
            return "structure", "hybrid 模式下 structure 停損虧損率較低且 ATR 安全倍數達標"
        return "volatility", "hybrid 模式下 volatility 停損虧損率較低且 ATR 安全倍數達標"

    if structure_valid and not volatility_valid:
        return "structure", "hybrid 模式排除過近的 volatility 停損，改用 structure 停損"

    if volatility_valid and not structure_valid:
        return "volatility", "hybrid 模式排除過近的 structure 停損，改用 volatility 停損"

    # two stops both too near -> choose the farther one
    if structure_stop_price <= volatility_stop_price:
        return "structure", "兩種停損距離都偏近，容易被正常波動洗出場，故選擇較遠停損"
    return "volatility", "兩種停損距離都偏近，容易被正常波動洗出場，故選擇較遠停損"


def _entry_price(target_price: float, stop_price: float, desired_rr: int) -> float:
    return (target_price + desired_rr * stop_price) / (desired_rr + 1)


def analyze_risk_reward(
    base: dict,
    mode: str,
    sliced_df: pd.DataFrame,
    trade_horizon: str,
    stop_method: str,
) -> dict:
    close = base["close"]
    ma20 = base["ma20"]
    ma60 = base["ma60"]
    recent_high = base["recent_high"]
    atr14 = base["atr14"]
    atr_pct = base["atr_pct"]
    volume = base["volume"]
    volume_ma20 = base["volume_ma20"]
    distance_to_recent_high_pct = base["distance_to_recent_high_pct"]
    lookback_days = base["lookback_days"]

    cfg = TRADE_HORIZON_CONFIG[trade_horizon]
    structure_stop_window = cfg["structure_stop_window"]
    atr_multiplier = cfg["atr_multiplier"]

    if len(sliced_df) < structure_stop_window:
        raise ValueError("資料不足，無法計算 trade_horizon 對應的 structure 停損")

    structure_stop_price = float(sliced_df["Low"].tail(structure_stop_window).min())
    volatility_stop_price = close - atr_multiplier * atr14

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

    structure_expected_loss_pct = _calc_loss_pct(close, structure_stop_price)
    volatility_expected_loss_pct = _calc_loss_pct(close, volatility_stop_price)

    structure_stop_atr_multiple = _calc_stop_atr_multiple(close, structure_stop_price, atr14)
    volatility_stop_atr_multiple = _calc_stop_atr_multiple(close, volatility_stop_price, atr14)

    structure_risk_reward_ratio = _calc_rr(expected_return_pct, structure_expected_loss_pct)
    volatility_risk_reward_ratio = _calc_rr(expected_return_pct, volatility_expected_loss_pct)

    if stop_method == "structure":
        selected_stop_method = "structure"
        selected_stop_reason = "依照 stop_method=structure，使用結構停損作為主要風險計算"
    elif stop_method == "volatility":
        selected_stop_method = "volatility"
        selected_stop_reason = "依照 stop_method=volatility，使用波動停損作為主要風險計算"
    else:
        selected_stop_method, selected_stop_reason = _select_hybrid_stop(
            close,
            atr14,
            expected_return_pct,
            structure_stop_price,
            volatility_stop_price,
        )

    selected_stop_price = structure_stop_price if selected_stop_method == "structure" else volatility_stop_price
    expected_loss_pct = _calc_loss_pct(close, selected_stop_price)
    stop_atr_multiple = _calc_stop_atr_multiple(close, selected_stop_price, atr14)
    risk_reward_ratio = _calc_rr(expected_return_pct, expected_loss_pct)

    volatility_level = get_volatility_level(atr_pct)
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

    if passed_filter and risk_grade in ["A", "B"]:
        action_suggestion = "符合目前篩選條件，可列入觀察清單，但仍需自行設定停損與部位控管。"
    elif risk_grade == "C":
        action_suggestion = "條件普通，風報比或波動尚未達到理想狀態，建議保守觀察。"
    else:
        action_suggestion = "目前風報比不足或風險過高，不適合直接追進場，較適合等待拉回或重新評估。"

    structure_entry_for_rr_2 = _entry_price(target_price, structure_stop_price, 2)
    structure_entry_for_rr_3 = _entry_price(target_price, structure_stop_price, 3)
    volatility_entry_for_rr_2 = _entry_price(target_price, volatility_stop_price, 2)
    volatility_entry_for_rr_3 = _entry_price(target_price, volatility_stop_price, 3)
    selected_entry_for_rr_2 = _entry_price(target_price, selected_stop_price, 2)
    selected_entry_for_rr_3 = _entry_price(target_price, selected_stop_price, 3)

    if close > selected_entry_for_rr_2 and close > selected_entry_for_rr_3:
        current_price_vs_entry_plan = "目前價格高於 RR=2 與 RR=3 的合理進場價，代表現在追進場風報比不足。"
    elif close <= selected_entry_for_rr_2 and close > selected_entry_for_rr_3:
        current_price_vs_entry_plan = "目前價格已接近 RR=2 的合理進場價，但距離 RR=3 仍偏高。"
    else:
        current_price_vs_entry_plan = "目前價格已落在 RR=3 的相對保守進場區附近，可搭配風險控管觀察。"

    reasons = [
        f"lookback={lookback_days} 代表使用近 {lookback_days} 個交易日判斷區間位置，不代表預計持有 {lookback_days} 天",
        f"{trade_horizon} 週期使用近 {structure_stop_window} 日低點與 {atr_multiplier} 倍 ATR 作為停損參考",
        f"structure 停損預估虧損為 {round_value(structure_expected_loss_pct):.2f}%，volatility 停損預估虧損為 {round_value(volatility_expected_loss_pct):.2f}%",
        f"{stop_method} 模式選擇 {selected_stop_method} 停損，原因：{selected_stop_reason}",
    ]

    if trend in ["bullish", "neutral_bullish"]:
        reasons.append("股價位於 MA20 與 MA60 之上，趨勢偏多")
    elif trend == "weak":
        reasons.append("股價低於 MA60，趨勢偏弱")
    else:
        reasons.append("趨勢中性，需等待更明確方向")

    reasons.append(
        f"預估報酬率為 {round_value(expected_return_pct):.2f}%，採用 {selected_stop_method} 停損後預估虧損率為 {round_value(expected_loss_pct):.2f}%，風報比為 {round_value(risk_reward_ratio) if risk_reward_ratio is not None else None}"
    )

    if 0 <= distance_to_recent_high_pct <= 5:
        reasons.append("目前價格接近 lookback 區間高點，上方空間有限，追價風報比偏低")

    if structure_stop_atr_multiple is not None and structure_stop_atr_multiple < 1.5 and volatility_stop_atr_multiple is not None and volatility_stop_atr_multiple < 1.5:
        reasons.append("兩種停損距離都偏近，容易被正常波動洗出場")

    reasons.append(f"{'符合' if passed_filter else '不符合'} {mode} 篩選條件")

    final_summary = (
        f"股價目前{('位於 MA20 與 MA60 之上，趨勢偏多' if trend in ['bullish', 'neutral_bullish'] else '趨勢偏弱或中性')}。"
        f"目前價格距離 lookback 區間高點約 {round_value(distance_to_recent_high_pct):.2f}%。"
        f"系統使用 {trade_horizon} 週期評估停損，採用 {selected_stop_method} 停損作為主要風險計算，"
        f"預估虧損 {round_value(expected_loss_pct):.2f}%、風報比 {round_value(risk_reward_ratio) if risk_reward_ratio is not None else None}。"
        f"整體來看，{('可列入觀察，但仍應嚴格控管風險' if passed_filter else '目前進場風報比不夠理想，較適合等待更佳位置')}。"
    )

    entry_plan = {
        "target_price": target_price,
        "structure_stop_price": structure_stop_price,
        "volatility_stop_price": volatility_stop_price,
        "selected_stop_price": selected_stop_price,
        "structure_entry_for_rr_2": structure_entry_for_rr_2,
        "structure_entry_for_rr_3": structure_entry_for_rr_3,
        "volatility_entry_for_rr_2": volatility_entry_for_rr_2,
        "volatility_entry_for_rr_3": volatility_entry_for_rr_3,
        "selected_entry_for_rr_2": selected_entry_for_rr_2,
        "selected_entry_for_rr_3": selected_entry_for_rr_3,
        "current_price_vs_entry_plan": current_price_vs_entry_plan,
    }

    output = {
        **base,
        "trade_horizon": trade_horizon,
        "stop_method": stop_method,
        "structure_stop_window": structure_stop_window,
        "atr_multiplier": atr_multiplier,
        "trend": trend,
        "target_price": target_price,
        "structure_stop_price": structure_stop_price,
        "volatility_stop_price": volatility_stop_price,
        "selected_stop_price": selected_stop_price,
        "selected_stop_method": selected_stop_method,
        "selected_stop_reason": selected_stop_reason,
        "structure_expected_loss_pct": structure_expected_loss_pct,
        "volatility_expected_loss_pct": volatility_expected_loss_pct,
        "expected_loss_pct": expected_loss_pct,
        "structure_stop_atr_multiple": structure_stop_atr_multiple,
        "volatility_stop_atr_multiple": volatility_stop_atr_multiple,
        "stop_atr_multiple": stop_atr_multiple,
        "expected_return_pct": expected_return_pct,
        "structure_risk_reward_ratio": structure_risk_reward_ratio,
        "volatility_risk_reward_ratio": volatility_risk_reward_ratio,
        "risk_reward_ratio": risk_reward_ratio,
        "volatility_level": volatility_level,
        "risk_grade": risk_grade,
        "passed_filter": passed_filter,
        "final_summary": final_summary,
        "action_suggestion": action_suggestion,
        "entry_plan": entry_plan,
        "reasons": reasons,
    }

    return output
