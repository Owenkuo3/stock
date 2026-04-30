import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from data_fetcher import fetch_ohlcv, resolve_effective_analysis_date
from indicators import add_indicators, validate_indicator_row
from strategies import analyze_momentum, analyze_risk_reward
from utils import (
    ALLOWED_LOOKBACKS,
    ALLOWED_MODES,
    ALLOWED_STOP_METHODS,
    ALLOWED_STRATEGIES,
    ALLOWED_TRADE_HORIZONS,
    parse_analysis_date,
)
from main import to_serializable


HTML_PAGE = """<!doctype html>
<html lang=\"zh-Hant\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Stock Strategy Analyzer</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 960px; margin: 24px auto; padding: 0 16px; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; }
    label { font-weight: 600; display:block; margin-bottom: 4px; }
    input, select, button { width: 100%; padding: 8px; box-sizing: border-box; }
    button { margin-top: 8px; cursor: pointer; }
    pre { background: #111; color: #ddd; padding: 12px; border-radius: 8px; overflow:auto; }
    .error { color: #b00020; }
  </style>
</head>
<body>
  <h1>Stock Strategy Analyzer Web UI</h1>
  <p>輸入參數後，按下「開始分析」即可得到和 CLI 一致的 JSON 結果。</p>

  <div class=\"grid\">
    <div><label>Symbol</label><input id=\"symbol\" value=\"AAPL\" /></div>
    <div><label>Lookback</label><select id=\"lookback\"><option>20</option><option selected>60</option><option>120</option><option>240</option></select></div>
    <div><label>Mode</label><select id=\"mode\"><option>loose</option><option selected>standard</option><option>strict</option></select></div>
    <div><label>Strategy</label><select id=\"strategy\"><option selected>risk_reward</option><option>momentum</option></select></div>
    <div><label>Analysis Date (選填 YYYY-MM-DD)</label><input id=\"analysis_date\" placeholder=\"2026-04-30\" /></div>
    <div><label>Trade Horizon</label><select id=\"trade_horizon\"><option>short</option><option selected>swing</option><option>position</option></select></div>
    <div><label>Stop Method</label><select id=\"stop_method\"><option>structure</option><option>volatility</option><option selected>hybrid</option></select></div>
  </div>

  <button id=\"run\">開始分析</button>
  <p id=\"status\"></p>
  <pre id=\"result\">尚未執行</pre>

  <script>
    document.getElementById('run').addEventListener('click', async () => {
      const payload = {
        symbol: document.getElementById('symbol').value.trim(),
        lookback: Number(document.getElementById('lookback').value),
        mode: document.getElementById('mode').value,
        strategy: document.getElementById('strategy').value,
        analysis_date: document.getElementById('analysis_date').value.trim() || null,
        trade_horizon: document.getElementById('trade_horizon').value,
        stop_method: document.getElementById('stop_method').value
      };

      const status = document.getElementById('status');
      const result = document.getElementById('result');
      status.textContent = '分析中...';
      status.className = '';

      try {
        const resp = await fetch('/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (!resp.ok) {
          status.textContent = '發生錯誤';
          status.className = 'error';
        } else {
          status.textContent = '完成';
          status.className = '';
        }
        result.textContent = JSON.stringify(data, null, 2);
      } catch (e) {
        status.textContent = '網路或伺服器錯誤';
        status.className = 'error';
        result.textContent = String(e);
      }
    });
  </script>
</body>
</html>
"""


def run_analysis(payload: dict) -> dict:
    symbol = (payload.get("symbol") or "").strip()
    lookback = int(payload.get("lookback", 0))
    mode = payload.get("mode")
    strategy = payload.get("strategy")
    analysis_date = payload.get("analysis_date")
    trade_horizon = payload.get("trade_horizon", "swing")
    stop_method = payload.get("stop_method", "hybrid")

    if not symbol:
        raise ValueError("symbol 不可為空")
    if lookback not in ALLOWED_LOOKBACKS:
        raise ValueError("lookback 不在允許值內，僅允許 20/60/120/240")
    if mode not in ALLOWED_MODES:
        raise ValueError("mode 不在允許值內，僅允許 loose/standard/strict")
    if strategy not in ALLOWED_STRATEGIES:
        raise ValueError("strategy 不在允許值內，僅允許 risk_reward/momentum")
    if trade_horizon not in ALLOWED_TRADE_HORIZONS:
        raise ValueError("trade_horizon 不在允許值內，僅允許 short/swing/position")
    if stop_method not in ALLOWED_STOP_METHODS:
        raise ValueError("stop_method 不在允許值內，僅允許 structure/volatility/hybrid")

    analysis_date_dt = parse_analysis_date(analysis_date)
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
        "analysis_date": analysis_date,
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


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path != "/":
            self.send_response(404)
            self.end_headers()
            return
        body = HTML_PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/analyze":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
            result = run_analysis(payload)
            self._json(200, result)
        except Exception as exc:  # noqa: BLE001
            self._json(400, {"ok": False, "error": str(exc)})


def main():
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now} UTC] Web UI running: http://localhost:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
