# stock-strategy-analyzer

`stock-strategy-analyzer` 是一個股票策略分析工具，支援 CLI 與 Web 介面，透過歷史日 K 資料評估目前進場位置。

## 專案定位（重要）

本工具是「K 線進場位置評論器」，不是「持有 N 天報酬預測器」。

- `lookback` 是觀察區間，不是持有天數。
- `lookback=60` 代表：用過去 60 個交易日判斷目前價格位置，不代表預計持有 60 天。
- 工具用來輔助判斷：
  - 是否接近前高、追高風險是否偏高
  - 是否靠近支撐、風報比是否較佳
  - 停損距離是否合理
  - 是否適合列入觀察

## 安裝方式

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## CLI 使用方式

```bash
python main.py \
  --symbol <SYMBOL> \
  --lookback <20|60|120|240> \
  --mode <loose|standard|strict> \
  --strategy <risk_reward|momentum> \
  [--analysis-date YYYY-MM-DD] \
  [--trade-horizon short|swing|position] \
  [--stop-method structure|volatility|hybrid]
```

- `--trade-horizon` 預設 `swing`，用來決定停損參考週期，不是報酬預測期間。
- `--stop-method` 預設 `hybrid`，用來決定主要停損價格的選擇方式。

## Web 使用方式

```bash
python web_app.py
```

啟動後開啟：

- `http://127.0.0.1:5000`

可直接在表單輸入：

- symbol
- lookback
- mode
- strategy
- analysis_date
- trade_horizon
- stop_method

按下「開始分析」後，會顯示 JSON 結果。

## 參數意義

### lookback（區間觀察）

- 用於 `recent_high` / `recent_low` / `target_price` / 區間位置判斷。
- 代表「看目前價格在大區間的位置」。

### trade_horizon（停損週期）

- 用於 `structure_stop_price` / `volatility_stop_price` / `selected_stop_price`。
- 代表「決定這次進場評估時，停損要看多短或多長」。

規則：

- `short`：`structure_stop_window=10`、`atr_multiplier=1.5`
- `swing`：`structure_stop_window=20`、`atr_multiplier=2.0`（預設）
- `position`：`structure_stop_window=60`、`atr_multiplier=2.5`

### stop_method（停損選擇方式）

- `structure`：`selected_stop_price = structure_stop_price`
- `volatility`：`selected_stop_price = volatility_stop_price`
- `hybrid`：同時計算兩種停損，依 ATR 安全倍數與虧損率選較合理者

## 日期規則

- `analysis_date` 未提供時，使用最新交易日。
- 若 `analysis_date` 不是交易日，會回退到前一個交易日。
- 所有指標只使用 `effective_analysis_date` 當日（含）以前資料，避免 future leakage。

## risk_reward 策略說明（本次重點）

策略核心問題：

> 目前價格作為進場點，風報比是否合理？停損距離是否可接受？

risk_reward 會同時輸出：

- `structure_stop_price`
- `volatility_stop_price`
- `selected_stop_price`
- `selected_stop_method`
- `selected_stop_reason`

並且主計算（`expected_loss_pct`、`risk_reward_ratio`、`risk_grade`、`passed_filter`）以 `selected_stop_price` 為準。

### 輔助決策輸出

- `final_summary`：白話總結目前位置與風險報酬結論。
- `action_suggestion`：對應風險等級的建議動作（非保證語氣）。
- `entry_plan`：反推 RR=2、RR=3 的參考進場價，幫助判斷是否追高。

## momentum 策略說明

`momentum` 保留第一版邏輯，用於評估轉強/加速動能，同時輸出動能與追高風險。

## 風險聲明

- 本工具不是投資建議，不保證未來報酬。
- 本工具不是未來價格預測器，而是進場位置評估輔助工具。
- `yfinance` 資料可能延遲或不完整，正式使用前請驗證資料來源。
