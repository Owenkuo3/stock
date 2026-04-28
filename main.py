import argparse
import json
import sys

from analyzer import run_analysis
from utils import (
    ALLOWED_LOOKBACKS,
    ALLOWED_MODES,
    ALLOWED_STOP_METHODS,
    ALLOWED_STRATEGIES,
    ALLOWED_TRADE_HORIZONS,
    error_json,
    parse_analysis_date,
)


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

        result = run_analysis(
            symbol=args.symbol,
            lookback=args.lookback,
            mode=args.mode,
            strategy=args.strategy,
            analysis_date_dt=analysis_date_dt,
            analysis_date_raw=args.analysis_date,
            trade_horizon=args.trade_horizon,
            stop_method=args.stop_method,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as exc:  # noqa: BLE001
        print(error_json(str(exc)))
        sys.exit(1)


if __name__ == "__main__":
    main()
