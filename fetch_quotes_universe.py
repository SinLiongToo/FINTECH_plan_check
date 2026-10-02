"""
fetch_quotes_universe.py — latest close for a *broad* ticker universe.

data/stock_data.json (fetch_stock_data.py) holds full weekly history for
~70 hand-picked tickers. That is too narrow for the Rebalance tool, where
users can add any ticker; browsers can't query Yahoo/TWSE directly (no
CORS headers) and the free public CORS proxies have proven unusable.

So this script, run by the same GitHub Actions workflow, writes a light
data/quotes.json with just name + latest close + date for:
  - TW: every TWSE-listed and TPEx (OTC) stock/ETF — two official open-data
    requests, no API key.
  - US: S&P 500 constituents + a curated list of popular ETFs / ADRs /
    large non-S&P names, priced in one batched yfinance download. Names
    come from Nasdaq Trader's symbol directory.

Format:
  {"as_of": "...", "tw": {"2337": ["旺宏", 122.0, "2026-10-02"], ...},
                   "us": {"TSM": ["Taiwan Semiconductor ...", 300.1, "2026-10-02"], ...}}

Each source is fetched independently; if one fails, the previous values
for that market are kept rather than wiped.
"""

import csv
import io
import json
import math
import re
import os
from datetime import datetime, timezone

import requests
import yfinance as yf

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "quotes.json")
UA = {"User-Agent": "Mozilla/5.0 (FinTech Toolkit data pipeline)"}

# Popular ETFs, ADRs and large US-listed names that are not in the S&P 500.
US_EXTRA = """
VT VTI VOO VEA VWO VXUS VNQ VIG VYM VUG VTV VB VO VGT VHT VDE VFH VPU VCR VDC VIS VAW VOX
BND BNDX BSV BIV BLV VGSH VGIT VGLT VTIP VCIT VCSH VCLT VMBS EDV
SPY IVV QQQ QQQM DIA IWM IWF IWD IWB IWN IWO IJH IJR MDY RSP
EFA EEM IEFA IEMG ACWI ACWX EWJ EWT EWY EWZ EWG EWU EWC EWA EWH MCHI FXI KWEB INDA VPL VGK
AGG TLT IEF SHY SHV BIL SGOV TIP LQD HYG JNK MUB EMB GOVT BOXX
SCHD SCHB SCHX SCHG SCHV SCHA SCHF SCHE SCHZ SCHP SCHH DGRO DVY HDV SDY NOBL JEPI JEPQ DIVO QYLD XYLD SPYD SPHD
XLK XLF XLV XLE XLY XLP XLI XLB XLU XLRE XLC SMH SOXX SOXL SOXS TQQQ SQQQ UPRO SPXL TECL
ARKK ARKW ARKG ARKQ ARKF ICLN TAN LIT URA BOTZ ROBO CIBR HACK SKYY CLOU IGV IBB XBI ITA XAR JETS KRE KBE
GLD IAU GLDM SLV PPLT USO UNG DBC PDBC GDX GDXJ COPX
IBIT FBTC GBTC ETHA BITO MSTR COIN
SPYM SPTM SPDW SPEM ITOT IXUS IUSB USMV MTUM QUAL VLUE SIZE COWZ AVUV AVDV DFAC DFUS
TSM ASML BABA PDD JD BIDU NIO LI XPEV TCEHY NVO AZN SAP SONY TM HMC SHOP SE MELI NU ARM BHP RIO
UL NVS TTE SHEL BP GSK SNY HSBC BCS UBS MUFG SMFG INFY HDB IBN WIT TCOM NTES BILI YMM
PLTR SNOW CRWD ZS NET DDOG MDB TEAM HUBS TWLO OKTA DOCU ZM ROKU XYZ PYPL SOFI HOOD AFRM RBLX U
SPOT UBER LYFT ABNB DASH RIVN LCID CVNA CHWY ETSY W PINS SNAP MRVL ASTS IONQ RGTI QBTS SMCI
""".split()


def roc_to_iso(s):
    """'1151002' (ROC calendar) -> '2026-10-02'."""
    s = (s or "").strip()
    if len(s) < 7 or not s.isdigit():
        return None
    return f"{int(s[:-4]) + 1911:04d}-{s[-4:-2]}-{s[-2:]}"


def num(v):
    try:
        f = float(str(v).replace(",", ""))
        return f if math.isfinite(f) and f > 0 else None
    except (TypeError, ValueError):
        return None


def fetch_twse():
    r = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", headers=UA, timeout=60)
    r.raise_for_status()
    out = {}
    for row in r.json():
        price = num(row.get("ClosingPrice"))
        if price:
            out[row["Code"].strip()] = [row["Name"].strip(), price, roc_to_iso(row.get("Date"))]
    return out


def fetch_tpex():
    r = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes", headers=UA, timeout=60)
    r.raise_for_status()
    out = {}
    for row in r.json():
        # Field names per TPEx open data docs; fall back to TWSE-style keys.
        code = (row.get("SecuritiesCompanyCode") or row.get("Code") or "").strip()
        price = num(row.get("Close") or row.get("ClosingPrice"))
        name = (row.get("CompanyName") or row.get("Name") or code).strip()
        if code and price:
            out[code] = [name, price, roc_to_iso(row.get("Date"))]
    return out


def fetch_tpex_via_yahoo():
    """Fallback when the TPEx site is down (it often 502s for hours): take the
    OTC code list from TWSE's ISIN registry and price it via yfinance (.TWO)."""
    r = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=4", headers=UA, timeout=90)
    r.raise_for_status()
    html = r.content.decode("big5", errors="ignore")
    names = {}
    for code, name in re.findall(r"<td bgcolor=#FAFAD2>(\w+)　([^<]+)</td>", html):
        # common stocks (4 digits) and ETFs (00xxx / 00xxxA); skip warrants etc.
        if re.fullmatch(r"\d{4}|00\d{3,4}[A-Z]?", code):
            names[code] = name.strip()
    return yahoo_close({c: c + ".TWO" for c in names}, names)


def yahoo_close(sym_map, names):
    """sym_map: our key -> Yahoo symbol. Returns {key: [name, close, date]}."""
    df = yf.download(sorted(set(sym_map.values())), period="7d", interval="1d", auto_adjust=False,
                     progress=False, group_by="column", threads=True)
    closes = df["Close"]
    out = {}
    for key, ys in sym_map.items():
        if ys not in closes:
            continue
        col = closes[ys].dropna()
        if col.empty:
            continue
        price = num(round(float(col.iloc[-1]), 4))
        if price:
            out[key] = [names.get(key) or key, price, col.index[-1].strftime("%Y-%m-%d")]
    return out


def us_names():
    names = {}
    for url, sym_col in (("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "Symbol"),
                         ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "ACT Symbol")):
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            for row in csv.DictReader(io.StringIO(r.text), delimiter="|"):
                sym, name = (row.get(sym_col) or "").strip(), (row.get("Security Name") or "").strip()
                if sym and name:
                    # Drop boilerplate like " - Common Stock" / " Class A Ordinary Shares"
                    name = name.split(" - ")[0]
                    name = re.sub(r"\s+(New\s+)?(Common Stock|Ordinary Shares|Class [A-C] (Common Stock|Ordinary Shares))$", "", name)
                    names[sym] = name.strip()
        except Exception as e:
            print(f"  ! symbol directory failed ({url}): {e}")
    return names


def sp500():
    r = requests.get("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
                     headers=UA, timeout=60)
    r.raise_for_status()
    return {row["Symbol"].strip(): row["Security"].strip() for row in csv.DictReader(io.StringIO(r.text))}


def fetch_us():
    try:
        universe = sp500()
    except Exception as e:
        print(f"  ! S&P 500 list failed: {e}")
        universe = {}
    for s in US_EXTRA:
        universe.setdefault(s, s)
    directory = us_names()
    names = {s: directory.get(s) or directory.get(s.replace(".", "-")) or universe[s] for s in universe}
    # Yahoo uses '-' for share classes (BRK.B -> BRK-B)
    return yahoo_close({s: s.replace(".", "-") for s in universe}, names)


def fetch_tpex_any():
    try:
        return fetch_tpex()
    except Exception as e:
        print(f"  ! TPEx open data failed ({e}); falling back to ISIN list + Yahoo .TWO")
        return fetch_tpex_via_yahoo()


def main():
    try:
        with open(OUT, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data.setdefault("tw", {})
    data.setdefault("us", {})

    for label, fn, market in (("TWSE", fetch_twse, "tw"), ("TPEx", fetch_tpex_any, "tw"), ("US", fetch_us, "us")):
        try:
            got = fn()
            data[market].update(got)
            print(f"  {label}: {len(got)} quotes")
        except Exception as e:
            print(f"  ! {label} failed, keeping previous values: {e}")

    data["as_of"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(f"Wrote {OUT}: tw={len(data['tw'])} us={len(data['us'])}")


if __name__ == "__main__":
    main()
