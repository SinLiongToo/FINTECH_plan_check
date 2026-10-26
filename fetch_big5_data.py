"""
fetch_big5_data.py — daily data for the 「大盤與五大權值」 page (tools/big5/).

Ported from the standalone "stock inculde big 5" project's update_prices.py,
with the same output format so the page works unchanged, but:
  - prices come from yfinance (same library as fetch_stock_data.py), which is
    more robust in CI than calling Yahoo's chart endpoint directly (direct
    calls hit HTTP 429 rate limits in testing);
  - output goes to data/big5_market_data.json, next to the other pipeline files.

Contents:
  - 1 year of daily OHLCV for TW Big 5 (2330, 2454, 2317, 2382, 2308), TAIEX,
    US indices (S&P 500, SOX, Nasdaq, Dow) and VT/VTI/BND/TSM/NVDA/GOOGL;
  - __MACRO_DATA__: monthly CPI/PMI series. Only US CPI / Core CPI are real and
    auto-updated (U.S. BLS public API, YoY computed here). TW CPI and the ISM /
    TW PMI series are the original project's built-in sample values — there is
    no free official API for them — and the page labels them as unverified.

Run by .github/workflows/daily_stock_update.yml (continue-on-error).
"""

import datetime
import json
import math
import os
import sys
import urllib.request

import yfinance as yf

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "big5_market_data.json")

SYMBOLS = {
    # Taiwan Big 5 & TAIEX (weights are the original project's approximations)
    "2330": {"yahoo": "2330.TW", "market": "TW", "currency": "TWD", "nameZh": "台積電", "nameEn": "TSMC", "weight": 0.345, "color": "#ef4444", "isDefault": True},
    "2454": {"yahoo": "2454.TW", "market": "TW", "currency": "TWD", "nameZh": "聯發科", "nameEn": "MediaTek", "weight": 0.035, "color": "#38bdf8", "isDefault": True},
    "2317": {"yahoo": "2317.TW", "market": "TW", "currency": "TWD", "nameZh": "鴻海", "nameEn": "Foxconn", "weight": 0.042, "color": "#a855f7", "isDefault": False},
    "2382": {"yahoo": "2382.TW", "market": "TW", "currency": "TWD", "nameZh": "廣達", "nameEn": "Quanta", "weight": 0.015, "color": "#f59e0b", "isDefault": False},
    "2308": {"yahoo": "2308.TW", "market": "TW", "currency": "TWD", "nameZh": "台達電", "nameEn": "Delta", "weight": 0.013, "color": "#10b981", "isDefault": False},
    "TAIEX": {"yahoo": "^TWII", "market": "TW", "currency": "Pts", "nameZh": "加權指數 (大盤)", "nameEn": "TAIEX", "weight": 1.0, "color": "#f43f5e", "isBenchmark": True, "isDefault": False},
    # US indices
    "SP500": {"yahoo": "^GSPC", "market": "US", "currency": "Pts", "nameZh": "標普 500 指數", "nameEn": "S&P 500 Index", "weight": 0.0, "color": "#f97316", "isBenchmark": True, "isDefault": True},
    "SOX": {"yahoo": "^SOX", "market": "US", "currency": "Pts", "nameZh": "費城半導體指數", "nameEn": "PHLX Semiconductor (SOX)", "weight": 0.0, "color": "#ec4899", "isBenchmark": True, "isDefault": True},
    "NASDAQ": {"yahoo": "^IXIC", "market": "US", "currency": "Pts", "nameZh": "那斯達克指數", "nameEn": "Nasdaq Composite", "weight": 0.0, "color": "#8b5cf6", "isBenchmark": True, "isDefault": True},
    "DJI": {"yahoo": "^DJI", "market": "US", "currency": "Pts", "nameZh": "道瓊工業指數", "nameEn": "Dow Jones Industrial", "weight": 0.0, "color": "#06b6d4", "isBenchmark": True, "isDefault": False},
    # US stocks & ETFs
    "VT": {"yahoo": "VT", "market": "US", "currency": "USD", "nameZh": "VT (全球股票ETF)", "nameEn": "Vanguard Total World ETF", "weight": 0.0, "color": "#0ea5e9", "isDefault": True},
    "VTI": {"yahoo": "VTI", "market": "US", "currency": "USD", "nameZh": "VTI (全美股票ETF)", "nameEn": "Vanguard Total Stock Market ETF", "weight": 0.0, "color": "#6366f1", "isDefault": True},
    "BND": {"yahoo": "BND", "market": "US", "currency": "USD", "nameZh": "BND (總體債券ETF)", "nameEn": "Vanguard Total Bond Market ETF", "weight": 0.0, "color": "#14b8a6", "isDefault": True},
    "TSM": {"yahoo": "TSM", "market": "US", "currency": "USD", "nameZh": "台積電 ADR", "nameEn": "TSMC ADR", "weight": 0.0, "color": "#fb7185", "isDefault": True},
    "NVDA": {"yahoo": "NVDA", "market": "US", "currency": "USD", "nameZh": "輝達 (NVIDIA)", "nameEn": "NVIDIA", "weight": 0.0, "color": "#84cc16", "isDefault": True},
    "GOOGL": {"yahoo": "GOOGL", "market": "US", "currency": "USD", "nameZh": "Google (Alphabet)", "nameEn": "Google (Alphabet)", "weight": 0.0, "color": "#eab308", "isDefault": True},
}

# The page's fixed 24-month macro window. US CPI / Core CPI inside it are
# overwritten from BLS; the other four series are the original sample values.
MACRO_MONTHS = [
    "2024-10", "2024-11", "2024-12", "2025-01", "2025-02", "2025-03",
    "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09",
    "2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
    "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09",
]
SAMPLE_SERIES = {
    "US_CPI":      [2.6, 2.7, 2.9, 3.0, 2.8, 2.6, 2.5, 2.4, 2.5, 2.6, 2.5, 2.4, 2.3, 2.4, 2.5, 2.4, 2.3, 2.2, 2.3, 2.2, 2.1, 2.2, 2.1, 2.1],
    "US_CORE_CPI": [3.3, 3.3, 3.2, 3.3, 3.1, 3.0, 2.9, 2.8, 2.8, 2.7, 2.7, 2.6, 2.6, 2.5, 2.5, 2.4, 2.4, 2.3, 2.3, 2.3, 2.2, 2.2, 2.2, 2.1],
    "TW_CPI":      [1.69, 2.08, 2.10, 2.66, 1.58, 2.14, 2.03, 1.92, 1.85, 2.15, 2.05, 1.88, 1.79, 1.82, 1.90, 2.25, 1.65, 1.78, 1.84, 1.76, 1.81, 1.94, 1.85, 1.78],
    "US_ISM_PMI":  [46.5, 48.4, 49.3, 50.9, 50.3, 49.8, 50.4, 51.2, 51.8, 52.1, 51.5, 52.4, 52.8, 53.1, 52.6, 53.4, 53.9, 53.2, 52.7, 53.5, 54.1, 53.8, 54.2, 54.6],
    "US_ISM_NMI":  [56.0, 52.1, 54.1, 52.8, 53.5, 53.1, 52.6, 53.8, 54.2, 54.5, 53.9, 54.8, 55.1, 54.7, 55.3, 54.9, 55.4, 55.0, 54.6, 55.2, 55.8, 55.5, 56.1, 56.3],
    "TW_PMI":      [50.0, 51.4, 50.8, 48.7, 54.0, 53.6, 54.2, 55.1, 55.8, 54.9, 54.3, 55.2, 56.0, 55.7, 56.4, 55.9, 56.8, 56.2, 55.5, 56.9, 57.4, 56.8, 57.2, 57.5],
}
UA = {"User-Agent": "Mozilla/5.0 (FinTech Toolkit data pipeline)"}


def num(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def fetch_prices():
    ysyms = [v["yahoo"] for v in SYMBOLS.values()]
    df = yf.download(ysyms, period="1y", interval="1d", auto_adjust=False, progress=False,
                     group_by="ticker", threads=True)
    out = {}
    for code, info in SYMBOLS.items():
        ys = info["yahoo"]
        if ys not in df.columns.get_level_values(0):
            print(f"  ! {code}: no data")
            continue
        sub = df[ys].dropna(subset=["Close"])
        series = []
        for idx, row in sub.iterrows():
            c = num(row["Close"])
            if c is None or c <= 0:
                continue
            h, l = num(row.get("High")), num(row.get("Low"))
            v = num(row.get("Volume")) or 0
            series.append({"date": idx.strftime("%Y-%m-%d"), "close": round(c, 2),
                           "high": round(h if h else c, 2), "low": round(l if l else c, 2),
                           "volume": int(v)})
        if not series:
            print(f"  ! {code}: empty series")
            continue
        out[code] = {
            "code": code, "market": info["market"], "currency": info["currency"],
            "nameZh": info["nameZh"], "nameEn": info["nameEn"], "color": info["color"],
            "weight": info["weight"], "isBenchmark": info.get("isBenchmark", False),
            "isDefault": info.get("isDefault", False),
            "latestDate": series[-1]["date"], "latestClose": series[-1]["close"],
            "count": len(series), "data": series,
        }
        print(f"  {code}: {len(series)} days, latest {series[-1]['date']} = {series[-1]['close']}")
    return out


def bls_yoy(series_id):
    """YoY % per YYYY-MM from the U.S. BLS public API (no key)."""
    # POST with an explicit year range: the GET form only returns ~3 years,
    # which isn't enough history to compute YoY for the window's first months.
    first_year = int(MACRO_MONTHS[0][:4]) - 1
    body = json.dumps({"seriesid": [series_id], "startyear": str(first_year),
                       "endyear": str(datetime.date.today().year)}).encode()
    req = urllib.request.Request("https://api.bls.gov/publicAPI/v1/timeseries/data/",
                                 data=body, headers=dict(UA, **{"Content-Type": "application/json"}))
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            payload = json.loads(r.read().decode("utf-8"))
        if payload.get("status") != "REQUEST_SUCCEEDED":
            return {}
        idx = {}
        for it in payload["Results"]["series"][0]["data"]:
            p, val = it.get("period", ""), str(it.get("value", "")).strip()
            if p.startswith("M") and p != "M13" and val not in ("-", "", "None"):
                idx[f"{it['year']}-{p[1:]}"] = float(val)
        yoy = {}
        for ym, v in idx.items():
            y, m = ym.split("-")
            prev = idx.get(f"{int(y) - 1}-{m}")
            if prev:
                yoy[ym] = round((v - prev) / prev * 100, 1)
        return yoy
    except Exception as e:  # network/API hiccup: keep the previous values
        print(f"  ! BLS {series_id} failed: {e}")
        return {}


def build_macro(previous):
    series = {k: list(v) for k, v in SAMPLE_SERIES.items()}
    # Keep earlier BLS values if this run can't reach the API.
    prev = (previous or {}).get("series", {})
    for k in ("US_CPI", "US_CORE_CPI"):
        if isinstance(prev.get(k), list) and len(prev[k]) == len(MACRO_MONTHS):
            series[k] = prev[k]
    # Months that hold an official BLS value (kept across runs if BLS is down).
    synced = {k: list(((previous or {}).get("officialMonths") or {}).get(k, [])) for k in ("US_CPI", "US_CORE_CPI")}
    for key, sid in (("US_CPI", "CUUR0000SA0"), ("US_CORE_CPI", "CUUR0000SA0L1E")):
        yoy = bls_yoy(sid)
        if yoy:
            synced[key] = []
        for i, ym in enumerate(MACRO_MONTHS):
            if ym in yoy:
                series[key][i] = yoy[ym]
                synced[key].append(ym)
        missing = [m for m in MACRO_MONTHS if m not in synced[key]]
        print(f"  BLS {key}: {len(synced[key])}/{len(MACRO_MONTHS)} official months; not published/available: {missing}")
    return {
        "lastUpdated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "months": MACRO_MONTHS,
        "series": series,
        "verified": ["US_CPI", "US_CORE_CPI"],
        "officialMonths": synced,
    }


def main():
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        old = {}
    prices = fetch_prices()
    data = dict(old)
    data.update(prices)  # symbols that failed keep their previous series
    data["__MACRO_DATA__"] = build_macro(old.get("__MACRO_DATA__"))
    data["__AS_OF__"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {OUT}: {len(prices)}/{len(SYMBOLS)} symbols refreshed")
    if not prices and not old:
        sys.exit(1)


if __name__ == "__main__":
    main()
