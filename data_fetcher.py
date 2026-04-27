from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


def fetch_ohlcv(symbol: str, lookback: int, analysis_date: datetime | None) -> pd.DataFrame:
    end_date = (analysis_date + timedelta(days=1)) if analysis_date else (datetime.utcnow() + timedelta(days=1))
    days_to_fetch = max(lookback + 200, 360)
    start_date = end_date - timedelta(days=int(days_to_fetch * 1.8))

    df = yf.download(
        symbol,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if df is None or df.empty:
        raise ValueError("symbol 抓不到資料或資料為空")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"資料欄位不足，缺少: {', '.join(missing_cols)}")

    df = df[required_cols].copy()
    df = df.dropna(subset=required_cols)
    df.index = pd.to_datetime(df.index).tz_localize(None)

    if df.empty:
        raise ValueError("symbol 抓不到有效 K 線資料")

    return df


def resolve_effective_analysis_date(df: pd.DataFrame, analysis_date: datetime | None) -> pd.Timestamp:
    trading_dates = df.index

    if analysis_date is None:
        return trading_dates[-1]

    if analysis_date < trading_dates[0].to_pydatetime():
        raise ValueError("analysis_date 早於資料起始日")

    eligible = trading_dates[trading_dates <= pd.Timestamp(analysis_date)]
    if len(eligible) == 0:
        raise ValueError("analysis_date 早於資料起始日")

    return eligible[-1]
