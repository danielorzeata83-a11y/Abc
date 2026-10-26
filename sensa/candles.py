"""Candles for the chart card: the intraday cache (intraday_server.py) when present,
else free Alpha Vantage daily bars (last ~100 sessions) for the 1day timeframe.
AV's intraday endpoint is premium, so 15m/30m/1h/4h need the cache."""

from markov.data_providers import DataUnavailable
from markov.intraday.service import get_candles


def _daily_candles(bars):
    days = _day_strings(bars.timestamps)
    return [{"time": d, "open": float(o), "high": float(h), "low": float(l),
             "close": float(c), "volume": float(v)}
            for d, o, h, l, c, v in zip(days, bars.open, bars.high, bars.low,
                                        bars.close, bars.volume)]


def _day_strings(ts):
    return [str(t)[:10] for t in ts.astype("datetime64[D]")]


def make_candles_fn(data_dir, daily=None, intraday=get_candles, secret="", yahoo=None):
    def candles(symbol, tf):
        try:
            return intraday(symbol, tf, data_dir)
        except DataUnavailable as cache_err:
            yahoo_err = None
            if yahoo is not None:                       # no key, no daily quota: all timeframes
                try:
                    return yahoo.candles(symbol.upper(), tf)
                except DataUnavailable as e:
                    yahoo_err = e
            if tf != "1day":
                if yahoo_err is not None:
                    raise DataUnavailable(f"{yahoo_err} (no local intraday cache either)") from None
                raise DataUnavailable(
                    f"{cache_err}. Intraday timeframes need the local cache "
                    "(Alpha Vantage intraday is a premium endpoint); try 1day.") from None
            if daily is None:
                raise DataUnavailable(
                    "No chart data: set ALPHAVANTAGE_API_KEY (free key) before starting "
                    "sensa_server.py to load daily candles.") from None
            try:
                return _daily_candles(daily.fetch(symbol.upper()))
            except DataUnavailable as e:
                msg = str(e).replace(secret, "***") if secret else str(e)
                raise DataUnavailable(msg) from None
    return candles
