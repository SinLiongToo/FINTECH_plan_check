#!/usr/bin/env python3
"""
fetch_stock_data.py - Stock data fetch for the FinTech Toolkit GitHub Pages site.

Runs inside a GitHub Actions workflow (not in the browser), fetches weekly
close-price history via yfinance for every ticker in TICKER_MAP, and writes
data/stock_data.json. The static site (GitHub Pages) only ever reads this
pre-computed JSON — it never calls Yahoo Finance from the browser, so there
is no CORS problem.

Adapted from the same pattern used in the
"FINICIAL ANNUAL REPORT DOWNLOAD TO MD_dashboard" project's
fetch_stock_data.py, trimmed down: no intraday bars (not needed for a
drawdown/rebalance tool) and a ticker map focused on what the Stock
Drawdown Explorer and Rebalance Engine tools actually use, plus a broad
set of US large-caps/ETFs for the "search US stocks" feature.

Usage:
    pip install -r requirements.txt
    python fetch_stock_data.py --all
    python fetch_stock_data.py --ticker aapl
"""

import os
import sys
import json
import time
import argparse
from datetime import date

import pandas as pd
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance is required. Install via: pip install -r requirements.txt")
    sys.exit(1)

# canonical slug -> {symbol, name, region, currency, exchange}
TICKER_MAP = {
    # --- Taiwan (used by Stock Drawdown Explorer's built-in 15 + TAIEX) ---
    "twii":  {"symbol": "^TWII",  "name": "TAIEX Index",  "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2330":  {"symbol": "2330.TW", "name": "TSMC",         "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2317":  {"symbol": "2317.TW", "name": "Hon Hai",      "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2454":  {"symbol": "2454.TW", "name": "MediaTek",     "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2303":  {"symbol": "2303.TW", "name": "UMC",          "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2308":  {"symbol": "2308.TW", "name": "Delta Elec",   "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2382":  {"symbol": "2382.TW", "name": "Quanta",       "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "3008":  {"symbol": "3008.TW", "name": "Largan",       "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2881":  {"symbol": "2881.TW", "name": "Fubon Fin",    "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2891":  {"symbol": "2891.TW", "name": "CTBC Fin",     "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2886":  {"symbol": "2886.TW", "name": "Mega Fin",     "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2002":  {"symbol": "2002.TW", "name": "China Steel",  "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "1301":  {"symbol": "1301.TW", "name": "Formosa Plas", "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "3711":  {"symbol": "3711.TW", "name": "ASE Tech",     "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "2412":  {"symbol": "2412.TW", "name": "Chunghwa Tel", "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},
    "0050":  {"symbol": "0050.TW", "name": "Yuanta Taiwan 50", "region": "Taiwan", "currency": "TWD", "exchange": "TWSE"},

    # --- Broad-market ETFs (used by Rebalance Engine defaults + general search) ---
    "vt":    {"symbol": "VT",   "name": "Vanguard Total World Stock",  "region": "United States", "currency": "USD", "exchange": "NYSE Arca"},
    "bnd":   {"symbol": "BND",  "name": "Vanguard Total Bond Market",  "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "voo":   {"symbol": "VOO",  "name": "Vanguard S&P 500",            "region": "United States", "currency": "USD", "exchange": "NYSE Arca"},
    "vti":   {"symbol": "VTI",  "name": "Vanguard Total Stock Market", "region": "United States", "currency": "USD", "exchange": "NYSE Arca"},
    "qqq":   {"symbol": "QQQ",  "name": "Invesco QQQ (Nasdaq 100)",    "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "spy":   {"symbol": "SPY",  "name": "SPDR S&P 500",                "region": "United States", "currency": "USD", "exchange": "NYSE Arca"},
    "soxx":  {"symbol": "SOXX", "name": "iShares Semiconductor",       "region": "United States", "currency": "USD", "exchange": "Nasdaq"},

    # --- US large-caps: search catalog for "US stock search" ---
    "aapl":  {"symbol": "AAPL",  "name": "Apple",                "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "msft":  {"symbol": "MSFT",  "name": "Microsoft",            "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "googl": {"symbol": "GOOGL", "name": "Alphabet (Google) A",  "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "amzn":  {"symbol": "AMZN",  "name": "Amazon",               "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "meta":  {"symbol": "META",  "name": "Meta Platforms",       "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "nvda":  {"symbol": "NVDA",  "name": "NVIDIA",               "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "tsla":  {"symbol": "TSLA",  "name": "Tesla",                "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "amd":   {"symbol": "AMD",   "name": "AMD",                  "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "intc":  {"symbol": "INTC",  "name": "Intel",                "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "avgo":  {"symbol": "AVGO",  "name": "Broadcom",             "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "qcom":  {"symbol": "QCOM",  "name": "Qualcomm",             "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "mu":    {"symbol": "MU",    "name": "Micron",               "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "crm":   {"symbol": "CRM",   "name": "Salesforce",           "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "orcl":  {"symbol": "ORCL",  "name": "Oracle",               "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "nflx":  {"symbol": "NFLX",  "name": "Netflix",              "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "dis":   {"symbol": "DIS",   "name": "Disney",               "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "jpm":   {"symbol": "JPM",   "name": "JPMorgan Chase",       "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "bac":   {"symbol": "BAC",   "name": "Bank of America",      "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "v":     {"symbol": "V",     "name": "Visa",                 "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "ma":    {"symbol": "MA",    "name": "Mastercard",           "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "wmt":   {"symbol": "WMT",   "name": "Walmart",              "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "hd":    {"symbol": "HD",    "name": "Home Depot",           "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "pg":    {"symbol": "PG",    "name": "Procter & Gamble",     "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "ko":    {"symbol": "KO",    "name": "Coca-Cola",            "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "pep":   {"symbol": "PEP",   "name": "PepsiCo",              "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "jnj":   {"symbol": "JNJ",   "name": "Johnson & Johnson",    "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "unh":   {"symbol": "UNH",   "name": "UnitedHealth",         "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "xom":   {"symbol": "XOM",   "name": "ExxonMobil",           "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "cvx":   {"symbol": "CVX",   "name": "Chevron",              "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "brk-b": {"symbol": "BRK-B", "name": "Berkshire Hathaway B", "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "pltr":  {"symbol": "PLTR",  "name": "Palantir",             "region": "United States", "currency": "USD", "exchange": "NYSE"},
    "arm":   {"symbol": "ARM",   "name": "Arm Holdings",         "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
    "asml":  {"symbol": "ASML",  "name": "ASML Holding",         "region": "United States", "currency": "USD", "exchange": "Nasdaq"},
}

# Weekly bars, not daily: matches the granularity of the tools' built-in
# GBM-interpolated data ("Weekly GBM data"), keeps history going back
# decades, and keeps data/stock_data.json small enough to live-commit
# twice a day without bloating the repo (daily bars for ~35 tickers over
# 10y would run several MB per commit; weekly is a fraction of that).
HIST_PERIOD = "max"
HIST_INTERVAL = "1wk"


def fetch_single_ticker(slug, meta):
    symbol = meta["symbol"]
    print(f"  [+] Fetching {slug} ({symbol})...", flush=True)

    df = None
    for attempt in range(1, 4):
        try:
            df = yf.Ticker(symbol).history(period=HIST_PERIOD, interval=HIST_INTERVAL, auto_adjust=True)
            if df is not None and not df.empty:
                break
        except Exception as e:
            if attempt == 3:
                print(f"    [!] Error fetching {symbol}: {e}")
                return None
        time.sleep(1.2 * attempt)

    if df is None or df.empty:
        print(f"    [!] Warning: empty history for {symbol}")
        return None

    df = df.dropna(subset=["Close"]).copy()
    dates = [idx.strftime("%Y-%m-%d") for idx in df.index]
    close = [round(float(v), 3) for v in df["Close"].tolist()]
    volume = [int(v) for v in df["Volume"].tolist()]

    curr = close[-1]
    prev = close[-2] if len(close) >= 2 else curr
    day_change = round(curr - prev, 3)
    day_change_pct = round((day_change / prev) * 100, 2) if prev else 0.0

    lookback = min(len(df), 52)
    w52_high = round(float(df["High"].iloc[-lookback:].max()), 3)
    w52_low = round(float(df["Low"].iloc[-lookback:].min()), 3)

    return {
        "status": "active",
        "company_slug": slug,
        "symbol": symbol,
        "name": meta.get("name", symbol),
        "region": meta.get("region", "Global"),
        "currency": meta.get("currency", "USD"),
        "exchange": meta.get("exchange", ""),
        "as_of": date.today().isoformat(),
        "current_price": curr,
        "day_change": day_change,
        "day_change_pct": day_change_pct,
        "w52_high": w52_high,
        "w52_low": w52_low,
        "latest_volume": volume[-1],
        "weekly": {
            "dates": dates,
            "close": close,
            "volume": volume,
        },
    }


def fetch_all(slugs=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(base_dir, "data", "stock_data.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    existing = {}
    if os.path.exists(out_file):
        try:
            with open(out_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    targets = slugs if slugs else list(TICKER_MAP.keys())
    print(f"\nFetching {len(targets)} tickers...")

    updated = 0
    for slug in targets:
        meta = TICKER_MAP.get(slug) or {"symbol": slug.upper(), "name": slug.upper(), "region": "Global", "currency": "USD", "exchange": ""}
        record = fetch_single_ticker(slug, meta)
        if record:
            existing[slug.lower()] = record
            existing[record["symbol"].lower()] = record
            if "." in record["symbol"]:
                existing[record["symbol"].split(".")[0].lower()] = record
            updated += 1
        time.sleep(0.6)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    size_kb = os.path.getsize(out_file) / 1024
    print(f"\nDone: {updated}/{len(targets)} updated. Saved to {out_file} ({size_kb:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(description="Fetch stock data for the FinTech Toolkit site.")
    parser.add_argument("--ticker", type=str, help="Fetch a single slug/symbol, e.g. aapl")
    parser.add_argument("--all", action="store_true", help="Fetch every ticker in TICKER_MAP")
    args = parser.parse_args()

    if args.ticker:
        fetch_all([args.ticker])
    else:
        fetch_all()


if __name__ == "__main__":
    main()
