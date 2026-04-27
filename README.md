# stock-strategy-analyzer

`stock-strategy-analyzer` 是一個以 CLI 執行的股票策略分析工具。輸入股票代號、分析週期、分析基準日、篩選模式與策略後，系統會抓取歷史日 K 資料、計算技術指標，並輸出 JSON 格式分析結果。

## 專案目的

- 快速評估股票在指定交易日的技術面狀態。
- 支援兩種第一版策略：
  - `risk_reward`：低風險風報比分析。
  - `momentum`：飆股/強勢動能分析。
- 第一版不包含：看跌模式、推播、AI 預測、自動下單、財報/新聞分析、回測系統。

## 安裝方式

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用方式

```bash
python main.py --symbol <SYMBOL> --lookback <20|60|120|240> --mode <loose|standard|strict> --strategy <risk_reward|momentum> [--analysis-date YYYY-MM-DD]
```

## CLI 範例

```bash
python main.py --symbol 2330.TW --lookback 60 --mode standard --strategy risk_reward
python main.py --symbol AAPL --lookback 120 --mode strict --strategy risk_reward --analysis-date 2025-10-01
python main.py --symbol 3661.TW --lookback 60 --mode standard --strategy momentum
python main.py --symbol TSLA --lookback 60 --mode strict --strategy momentum --analysis-date 2025-10-01
```

## 日期與 lookback 規則

- `lookback` 代表**交易日**，不是自然日。
- `analysis_date` 是分析基準日。
- 若未提供 `analysis_date`，預設使用最新交易日。
- 若 `analysis_date` 不是交易日，會回退到該日期之前最近一個交易日作為 `effective_analysis_date`。
- 所有指標僅使用 `effective_analysis_date` 當日（含）之前資料，避免 future leakage。

## 策略說明

### 1) risk_reward

評估目前進場位置的：

- 預估報酬率（以 lookback 區間高點為目標價）
- 預估虧損率（結構停損 vs 2ATR 停損取較低價）
- 風報比
- 波動等級與風險等級

#### risk_reward 風險等級規則

- E 級優先：`trend == weak` 或 `expected_loss_pct > 10` 或 `atr_pct >= 8` 或 `expected_return_pct <= 0`。
- A/B/C/D 依風報比、趨勢與預估虧損率判定。
- 若波動等級為 `extreme`，最高只能給 C。

### 2) momentum

評估是否有轉強/加速動能，同時量化追高風險。

輸出包含：

- `momentum_score`（動能分數）
- `momentum_grade`（動能等級）
- `risk_score`（追高/波動/假突破/流動性風險分數）
- `risk_level`
- `final_decision`

#### momentum 動能分數規則

動能分數（0~100）整合以下訊號：

- 是否突破或接近 lookback 高點
- 當日量能與量能趨勢
- 均線結構（多頭排列）
- 5 日/20 日漲幅
- 價格是否在 MA20/MA60 之上
- 並考慮過熱與過高波動扣分，及破線/量縮上限限制

#### momentum 風險分數規則

風險分數（0~100，越高越危險）整合：

- ATR 波動風險
- 價格距 MA20 過遠
- 5 日/20 日漲幅過熱
- 假突破風險（量價背離）
- 上影線風險
- 流動性風險（第一版用 20 日均量粗估）

> 注意：台股與美股成交量單位不同，流動性分數門檻應依市場特性調整。

## ATR 與波動風險說明

ATR14 使用 True Range 的 14 日平均：

- `TR = max(High-Low, abs(High-PrevClose), abs(Low-PrevClose))`
- `atr_pct = ATR14 / Close * 100`

atr_pct 越高，代表單日平均波動越大，停損被洗出的機率通常越高。

## 錯誤處理

錯誤統一輸出 JSON：

```json
{
  "error": "錯誤訊息"
}
```

包含：symbol 無效、參數不合法、日期格式錯誤、資料不足、指標 NaN 等。

## 免責聲明

- 本工具不是投資建議，僅根據歷史 K 線進行量化分析。
- `yfinance` 資料可能延遲或不完整，正式使用前請驗證資料來源。
