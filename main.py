import argparse
import json
import sys

from data_fetcher import fetch_ohlcv, resolve_effective_analysis_date
from indicators import add_indicators, validate_indicator_row
from strategies import analyze_momentum, analyze_risk_reward
from utils import (
    ALLOWED_LOOKBACKS,
    ALLOWED_MODES,
    ALLOWED_STOP_METHODS,
    ALLOWED_STRATEGIES,
    ALLOWED_TRADE_HORIZONS,
    error_json,
    parse_analysis_date,
    round_value,
)


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


def parse_args():
    parser = argparse.ArgumentParser(description="Stock strategy analyzer")
    parser.add_argument("--symbol", required=True, type=str)
    parser.add_argument("--lookback", required=True, type=int)
    parser.add_argument("--mode", required=True, type=str)
    parser.add_argument("--strategy", required=True, type=str)
    parser.add_argument("--analysis-date", required=False, type=str, default=None)
    parser.add_argument("--trade-horizon", required=False, type=str, default="swing")
    parser.add_argument("--stop-method", required=False, type=str, default="hybrid")
    return parser.parse_args()


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


def main():
    args = parse_args()

    try:
        if args.lookback not in ALLOWED_LOOKBACKS:
            raise ValueError("lookback 不在允許值內，僅允許 20/60/120/240")
        if args.mode not in ALLOWED_MODES:
            raise ValueError("mode 不在允許值內，僅允許 loose/standard/strict")
        if args.strategy not in ALLOWED_STRATEGIES:
            raise ValueError("strategy 不在允許值內，僅允許 risk_reward/momentum")
        if args.trade_horizon not in ALLOWED_TRADE_HORIZONS:
            raise ValueError("trade_horizon 不在允許值內，僅允許 short/swing/position")
        if args.stop_method not in ALLOWED_STOP_METHODS:
            raise ValueError("stop_method 不在允許值內，僅允許 structure/volatility/hybrid")

        analysis_date_dt = parse_analysis_date(args.analysis_date)

        df = fetch_ohlcv(args.symbol, args.lookback, analysis_date_dt)
        effective_date = resolve_effective_analysis_date(df, analysis_date_dt)

        sliced = df[df.index <= effective_date].copy()
        needed_len = max(args.lookback + 120, args.lookback + 14, 240)
        if len(sliced) < needed_len:
            raise ValueError("資料不足，無法計算 MA120 或 lookback 區間")

        with_ind = add_indicators(sliced, args.lookback)
        row = with_ind.loc[effective_date]
        validate_indicator_row(row)

        base = {
            "symbol": args.symbol,
            "strategy": args.strategy,
            "analysis_date": args.analysis_date,
            "effective_analysis_date": effective_date.strftime("%Y-%m-%d"),
            "close": float(row["Close"]),
            "volume": float(row["Volume"]),
            "lookback_days": args.lookback,
            "filter_mode": args.mode,
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

        if args.strategy == "risk_reward":
            result = analyze_risk_reward(
                base=base,
                mode=args.mode,
                sliced_df=sliced,
                trade_horizon=args.trade_horizon,
                stop_method=args.stop_method,
            )
        else:
            result = analyze_momentum(base, args.mode, row.to_dict())

        result = to_serializable(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as exc:  # noqa: BLE001
        print(error_json(str(exc)))
        sys.exit(1)


if __name__ == "__main__":
    main()
