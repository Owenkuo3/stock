import json

from flask import Flask, render_template, request

from analyzer import run_analysis
from utils import (
    ALLOWED_LOOKBACKS,
    ALLOWED_MODES,
    ALLOWED_STOP_METHODS,
    ALLOWED_STRATEGIES,
    ALLOWED_TRADE_HORIZONS,
    parse_analysis_date,
)

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    form_data = {
        "symbol": "AAPL",
        "lookback": "60",
        "mode": "standard",
        "strategy": "risk_reward",
        "analysis_date": "",
        "trade_horizon": "swing",
        "stop_method": "hybrid",
    }
    result_json = ""
    error = ""

    if request.method == "POST":
        form_data.update({
            "symbol": request.form.get("symbol", "").strip(),
            "lookback": request.form.get("lookback", "60"),
            "mode": request.form.get("mode", "standard"),
            "strategy": request.form.get("strategy", "risk_reward"),
            "analysis_date": request.form.get("analysis_date", "").strip(),
            "trade_horizon": request.form.get("trade_horizon", "swing"),
            "stop_method": request.form.get("stop_method", "hybrid"),
        })

        try:
            lookback = int(form_data["lookback"])
            if lookback not in ALLOWED_LOOKBACKS:
                raise ValueError("lookback 不在允許值內")
            if form_data["mode"] not in ALLOWED_MODES:
                raise ValueError("mode 不在允許值內")
            if form_data["strategy"] not in ALLOWED_STRATEGIES:
                raise ValueError("strategy 不在允許值內")
            if form_data["trade_horizon"] not in ALLOWED_TRADE_HORIZONS:
                raise ValueError("trade_horizon 不在允許值內")
            if form_data["stop_method"] not in ALLOWED_STOP_METHODS:
                raise ValueError("stop_method 不在允許值內")

            analysis_date_raw = form_data["analysis_date"] or None
            analysis_date_dt = parse_analysis_date(analysis_date_raw)

            result = run_analysis(
                symbol=form_data["symbol"],
                lookback=lookback,
                mode=form_data["mode"],
                strategy=form_data["strategy"],
                analysis_date_dt=analysis_date_dt,
                analysis_date_raw=analysis_date_raw,
                trade_horizon=form_data["trade_horizon"],
                stop_method=form_data["stop_method"],
            )
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

    return render_template(
        "index.html",
        form_data=form_data,
        result_json=result_json,
        error=error,
        lookbacks=sorted(ALLOWED_LOOKBACKS),
        modes=sorted(ALLOWED_MODES),
        strategies=sorted(ALLOWED_STRATEGIES),
        trade_horizons=sorted(ALLOWED_TRADE_HORIZONS),
        stop_methods=sorted(ALLOWED_STOP_METHODS),
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
