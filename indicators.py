import numpy as np
import pandas as pd


REQUIRED_INDICATOR_COLUMNS = [
    "MA5",
    "MA10",
    "MA20",
    "MA60",
    "MA120",
    "ATR14",
    "volume_ma5",
    "volume_ma20",
    "recent_high",
    "recent_low",
    "return_5d_pct",
    "return_20d_pct",
    "return_60d_pct",
    "distance_to_ma20_pct",
    "distance_to_recent_high_pct",
    "distance_to_recent_low_pct",
    "atr_pct",
]


def add_indicators(df: pd.DataFrame, lookback: int) -> pd.DataFrame:
    out = df.copy()

    out["MA5"] = out["Close"].rolling(5).mean()
    out["MA10"] = out["Close"].rolling(10).mean()
    out["MA20"] = out["Close"].rolling(20).mean()
    out["MA60"] = out["Close"].rolling(60).mean()
    out["MA120"] = out["Close"].rolling(120).mean()

    prev_close = out["Close"].shift(1)
    tr = np.maximum.reduce(
        [
            (out["High"] - out["Low"]).to_numpy(),
            (out["High"] - prev_close).abs().to_numpy(),
            (out["Low"] - prev_close).abs().to_numpy(),
        ]
    )
    out["TR"] = tr
    out["ATR14"] = out["TR"].rolling(14).mean()

    out["volume_ma5"] = out["Volume"].rolling(5).mean()
    out["volume_ma20"] = out["Volume"].rolling(20).mean()

    out["recent_high"] = out["High"].rolling(lookback).max()
    out["recent_low"] = out["Low"].rolling(lookback).min()

    out["return_5d_pct"] = (out["Close"] / out["Close"].shift(5) - 1.0) * 100
    out["return_20d_pct"] = (out["Close"] / out["Close"].shift(20) - 1.0) * 100
    out["return_60d_pct"] = (out["Close"] / out["Close"].shift(60) - 1.0) * 100

    out["distance_to_ma20_pct"] = (out["Close"] - out["MA20"]) / out["Close"] * 100
    out["distance_to_recent_high_pct"] = (out["recent_high"] - out["Close"]) / out["Close"] * 100
    out["distance_to_recent_low_pct"] = (out["Close"] - out["recent_low"]) / out["Close"] * 100
    out["atr_pct"] = out["ATR14"] / out["Close"] * 100

    return out


def validate_indicator_row(row: pd.Series):
    for col in REQUIRED_INDICATOR_COLUMNS:
        if pd.isna(row.get(col)):
            raise ValueError("資料不足，無法計算 MA120 / ATR14 / lookback 區間")
