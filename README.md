# btc-cent-forecast-01

Entry for [make.fun bounty btc-cent-forecast-01](https://make.fun/bounty/btc-cent-forecast-01): forecast BTC/USDC's close 4 hours ahead from 72 hours of one-minute closes.

## Method

1. **Persistence** — start from the last close in the case.
2. **Mean reversion** — shrink that guess 50% toward the mean of the last 360 closes (6 hours).

Python 3.13, standard library only, deterministic, no network.

## Run

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `*.in` under the input dir (name order) and writes matching `*.out` files as:

```json
{"forecasts":[{"case":"p00","price":62100.25}]}
```
