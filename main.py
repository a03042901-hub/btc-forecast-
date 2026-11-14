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
# make.fun price grid is 5 decimals; keep output in (0, 1e7).
PRICE_DECIMALS = 5
PRICE_MAX = 10_000_000.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def as_price(x: object) -> float | None:
    """Parse a finite positive price, or None if unusable."""
    try:
        v = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v) or v <= 0 or v >= PRICE_MAX:
        return None
    return v


def parse_prices(raw: object) -> list[float]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("prices must be a non-empty list")
    out: list[float] = []
    for item in raw:
        v = as_price(item)
        if v is None:
            raise ValueError(f"invalid price: {item!r}")
        out.append(v)
    return out


def forecast_price(prices: list[float]) -> float:
    """Persistence shrunk 50% toward the mean of the last LOOKBACK closes."""
    last = prices[-1]
    window = prices[-LOOKBACK:] if len(prices) >= LOOKBACK else prices
    m = mean(window)
    # last + SHRINK * (m - last)  ==  (1 - SHRINK) * last + SHRINK * m
    guess = (1.0 - SHRINK) * last + SHRINK * m
    if not math.isfinite(guess) or guess <= 0:
        guess = last
    # Clamp and round to the recording's 5-decimal grid.
    guess = min(max(guess, sys.float_info.min), PRICE_MAX - sys.float_info.epsilon)
    return round(guess, PRICE_DECIMALS)


def btc_prices(case: dict) -> list[float]:
    markets = case.get("markets")
    if not isinstance(markets, list) or not markets:
        raise ValueError("case has no markets")
    chosen = None
    for market in markets:
        if isinstance(market, dict) and market.get("id") == "btc-usdc":
            chosen = market
            break
    if chosen is None:
        chosen = markets[0] if isinstance(markets[0], dict) else None
    if not isinstance(chosen, dict):
        raise ValueError("market entry is not an object")
    return parse_prices(chosen.get("prices"))


def run_case(case: dict, case_id: str) -> dict:
    if not isinstance(case, dict):
        raise ValueError("case JSON must be an object")
    # Prefer the id inside the file when present; fall back to the filename stem.
    declared = case.get("case")
    if isinstance(declared, str) and declared:
        case_id = declared
    prices = btc_prices(case)
    price = forecast_price(prices)
    return {"forecasts": [{"case": case_id, "price": price}]}


def main() -> None:
    input_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    if not input_dir.is_dir():
        raise FileNotFoundError(f"input dir not found: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs = sorted(
        p for p in input_dir.iterdir() if p.is_file() and p.name.endswith(".in")
    )
    if not inputs:
        raise FileNotFoundError(f"no *.in files in {input_dir}")

    for path in inputs:
        case_id = path.name[: -len(".in")]
        if not case_id:
            raise ValueError(f"empty case id from {path.name}")
        with path.open("r", encoding="utf-8") as f:
            case = json.load(f)
        out = run_case(case, case_id)
        out_path = output_dir / f"{case_id}.out"
        # Compact JSON, trailing newline; keys in forecasts row stay case then price.
        payload = json.dumps(out, separators=(",", ":"), ensure_ascii=False)
        with out_path.open("w", encoding="utf-8") as f:
            f.write(payload)
            f.write("\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — surface any failure to the grader
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
