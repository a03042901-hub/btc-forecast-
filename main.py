#!/usr/bin/env python3
"""BTC/USDC 4-hour ahead forecaster for make.fun btc-cent-forecast-01.

Reads every /input/<id>.in (or $MAKEFUN_INPUT_DIR), forecasts the close
240 minutes ahead, and writes /output/<id>.out (or $MAKEFUN_OUTPUT_DIR).

Method: persistence (last close), then shrink 50% toward the mean of the
last 360 one-minute closes. Deterministic; standard library only.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

LOOKBACK = 360
SHRINK = 0.5


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def forecast_price(prices: list[float]) -> float:
    """Persistence shrunk 50% toward the mean of the last LOOKBACK closes."""
    last = prices[-1]
    window = prices[-LOOKBACK:] if len(prices) >= LOOKBACK else prices
    m = mean(window)
    # last + SHRINK * (m - last)  ==  (1 - SHRINK) * last + SHRINK * m
    return (1.0 - SHRINK) * last + SHRINK * m


def btc_prices(case: dict) -> list[float]:
    markets = case.get("markets") or []
    for market in markets:
        if market.get("id") == "btc-usdc":
            prices = market.get("prices") or []
            if prices:
                return [float(p) for p in prices]
    if markets and markets[0].get("prices"):
        return [float(p) for p in markets[0]["prices"]]
    raise ValueError("case has no prices")


def run_case(case: dict, case_id: str) -> dict:
    prices = btc_prices(case)
    price = forecast_price(prices)
    if not math.isfinite(price) or price <= 0:
        price = prices[-1]
    return {"forecasts": [{"case": case_id, "price": price}]}


def main() -> None:
    input_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs = sorted(p for p in input_dir.iterdir() if p.is_file() and p.name.endswith(".in"))
    for path in inputs:
        case_id = path.name[: -len(".in")]
        with path.open("r", encoding="utf-8") as f:
            case = json.load(f)
        out = run_case(case, case.get("case", case_id))
        out_path = output_dir / f"{case_id}.out"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
            f.write("\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — exit non-zero on any failure
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
