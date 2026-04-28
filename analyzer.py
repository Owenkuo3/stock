from data_fetcher import fetch_ohlcv, resolve_effective_analysis_date
from indicators import add_indicators, validate_indicator_row
from strategies import analyze_momentum, analyze_risk_reward
from utils import round_value


COMMON_NUMERIC_FIELDS = [
    "close",
    "volume",
    "ma5",
    "ma10",
    "ma20",
    "ma60",
    "ma120",
    "volume_ma5",
    "volume_ma20",
    "atr14",
    "atr_pct",
    "recent_high",
    "recent_low",
    "return_5d_pct",
    "return_20d_pct",
    "return_60d_pct",
    "distance_to_ma20_pct",
    "distance_to_recent_high_pct",
    "distance_to_recent_low_pct",
]


RISK_REWARD_NUMERIC_FIELDS = [
    "structure_stop_window",
    "atr_multiplier",
    "target_price",
    "structure_stop_price",
    "volatility_stop_price",
    "selected_stop_price",
    "structure_expected_loss_pct",
    "volatility_expected_loss_pct",
    "expected_loss_pct",
    "structure_stop_atr_multiple",
    "volatility_stop_atr_multiple",
    "stop_atr_multiple",
    "expected_return_pct",
    "structure_risk_reward_ratio",
    "volatility_risk_reward_ratio",
    "risk_reward_ratio",
]


def _round_nested_entry_plan(entry_plan: dict):
    rounded = {}
    for key, value in entry_plan.items():
        if isinstance(value, (int, float)):
            rounded[key] = round_value(value, 2)
        else:
            rounded[key] = value
    return rounded


def to_serializable(result: dict):
    for key in list(result.keys()):
        if key in COMMON_NUMERIC_FIELDS or key in RISK_REWARD_NUMERIC_FIELDS or key.endswith("_pct") or key.endswith("_price") or key.endswith("_ratio") or key.endswith("_multiple"):
            result[key] = round_value(result[key], 2)

    if "entry_plan" in result and isinstance(result["entry_plan"], dict):
        result["entry_plan"] = _round_nested_entry_plan(result["entry_plan"])

    return result


def run_analysis(
    symbol: str,
    lookback: int,
    mode: str,
    strategy: str,
    analysis_date_dt,
    analysis_date_raw,
    trade_horizon: str,
    stop_method: str,
):
    df = fetch_ohlcv(symbol, lookback, analysis_date_dt)
    effective_date = resolve_effective_analysis_date(df, analysis_date_dt)

    sliced = df[df.index <= effective_date].copy()
    needed_len = max(lookback + 120, lookback + 14, 240)
    if len(sliced) < needed_len:
        raise ValueError("資料不足，無法計算 MA120 或 lookback 區間")

    with_ind = add_indicators(sliced, lookback)
    row = with_ind.loc[effective_date]
    validate_indicator_row(row)

    base = {
        "symbol": symbol,
        "strategy": strategy,
        "analysis_date": analysis_date_raw,
        "effective_analysis_date": effective_date.strftime("%Y-%m-%d"),
        "close": float(row["Close"]),
        "volume": float(row["Volume"]),
        "lookback_days": lookback,
        "filter_mode": mode,
        "ma5": float(row["MA5"]),
        "ma10": float(row["MA10"]),
        "ma20": float(row["MA20"]),
        "ma60": float(row["MA60"]),
        "ma120": float(row["MA120"]),
        "volume_ma5": float(row["volume_ma5"]),
        "volume_ma20": float(row["volume_ma20"]),
        "atr14": float(row["ATR14"]),
        "atr_pct": float(row["atr_pct"]),
        "recent_high": float(row["recent_high"]),
        "recent_low": float(row["recent_low"]),
        "return_5d_pct": float(row["return_5d_pct"]),
        "return_20d_pct": float(row["return_20d_pct"]),
        "return_60d_pct": float(row["return_60d_pct"]),
        "distance_to_ma20_pct": float(row["distance_to_ma20_pct"]),
        "distance_to_recent_high_pct": float(row["distance_to_recent_high_pct"]),
        "distance_to_recent_low_pct": float(row["distance_to_recent_low_pct"]),
    }

    if strategy == "risk_reward":
        result = analyze_risk_reward(
            base=base,
            mode=mode,
            sliced_df=sliced,
            trade_horizon=trade_horizon,
            stop_method=stop_method,
        )
    else:
        result = analyze_momentum(base, mode, row.to_dict())

    return to_serializable(result)
