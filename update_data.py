"""Refresh the kit's data with TODAY's numbers via yfinance (free, no API key).

Runs on your own machine (where the network is open). Install once:

    pip install yfinance

Then refresh fundamentals for the screener / valuation cards:

    python update_data.py --fundamentals --tickers AAPL,MSFT,NVDA,XOM,JPM,KO
    python update_data.py --fundamentals --from-existing      # reuse current symbol list

...or refresh the price panel (for dashboard.py / chart_cli.py):

    python update_data.py --prices --tickers AAPL,MSFT,NVDA --years 6

Notes:
- yfinance is rate-limited and occasionally flaky; keep lists modest and
  re-run if some tickers fail (they are skipped, not fatal).
- Writes data/sp500_financials.csv and/or data/sp500.csv in the kit's own
  data folder, so the other tools pick them up automatically.
- This refreshes valuation CONTEXT, not a buy signal. Not investment advice.
"""

import argparse
import os

import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

FIN_COLS = ["Symbol", "Name", "Sector", "Price", "Price/Earnings",
            "Dividend Yield", "Earnings/Share", "52 Week Low", "52 Week High",
            "Market Cap", "EBITDA", "Price/Sales", "Price/Book", "SEC Filings"]


def _symbols(args):
    if args.tickers:
        return [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if args.from_existing:
        path = os.path.join(DATA, "sp500_financials.csv")
        return pd.read_csv(path)["Symbol"].tolist()
    raise SystemExit("pass --tickers A,B,C or --from-existing")


def update_fundamentals(tickers):
    import yfinance as yf
    rows, skipped = [], []
    for i, t in enumerate(tickers, 1):
        try:
            info = yf.Ticker(t).info
            dy = info.get("dividendYield")
            if dy and dy > 1:        # some versions report percent, not fraction
                dy = dy / 100.0
            rows.append({
                "Symbol": t,
                "Name": info.get("shortName", t),
                "Sector": info.get("sector", "Unknown"),
                "Price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "Price/Earnings": info.get("trailingPE"),
                "Dividend Yield": dy,
                "Earnings/Share": info.get("trailingEps"),
                "52 Week Low": info.get("fiftyTwoWeekLow"),
                "52 Week High": info.get("fiftyTwoWeekHigh"),
                "Market Cap": info.get("marketCap"),
                "EBITDA": info.get("ebitda"),
                "Price/Sales": info.get("priceToSalesTrailing12Months"),
                "Price/Book": info.get("priceToBook"),
                "SEC Filings": "",
            })
            print(f"  [{i}/{len(tickers)}] {t} ok")
        except Exception as exc:  # noqa: BLE001
            skipped.append(t)
            print(f"  [{i}/{len(tickers)}] {t} skipped ({exc})")
    if not rows:
        raise SystemExit("no fundamentals fetched (check internet / tickers)")
    df = pd.DataFrame(rows, columns=FIN_COLS)
    out = os.path.join(DATA, "sp500_financials.csv")
    df.to_csv(out, index=False)
    print(f"\nWrote {len(df)} stocks -> {out}  (skipped {len(skipped)})")


def update_prices(tickers, years):
    import yfinance as yf
    period = f"{years}y"
    frames = []
    for i, t in enumerate(tickers, 1):
        try:
            h = yf.Ticker(t).history(period=period, auto_adjust=False)
            if h.empty:
                print(f"  [{i}/{len(tickers)}] {t} empty"); continue
            h = h.reset_index()[["Date", "Open", "High", "Low", "Close", "Volume"]]
            h.columns = ["date", "open", "high", "low", "close", "volume"]
            h["date"] = pd.to_datetime(h["date"]).dt.date
            h["Name"] = t
            frames.append(h)
            print(f"  [{i}/{len(tickers)}] {t} ok ({len(h)} rows)")
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(tickers)}] {t} skipped ({exc})")
    if not frames:
        raise SystemExit("no prices fetched")
    out = os.path.join(DATA, "sp500.csv")
    pd.concat(frames, ignore_index=True).to_csv(out, index=False)
    print(f"\nWrote price panel -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fundamentals", action="store_true")
    ap.add_argument("--prices", action="store_true")
    ap.add_argument("--tickers", default=None, help="comma list, e.g. AAPL,MSFT")
    ap.add_argument("--from-existing", action="store_true",
                    help="reuse the symbols already in sp500_financials.csv")
    ap.add_argument("--years", type=int, default=6)
    args = ap.parse_args()
    if not (args.fundamentals or args.prices):
        raise SystemExit("choose --fundamentals and/or --prices")
    tickers = _symbols(args)
    if args.fundamentals:
        print(f"Fundamentals for {len(tickers)} tickers via yfinance...")
        update_fundamentals(tickers)
    if args.prices:
        print(f"Prices ({args.years}y) for {len(tickers)} tickers via yfinance...")
        update_prices(tickers, args.years)


if __name__ == "__main__":
    main()
