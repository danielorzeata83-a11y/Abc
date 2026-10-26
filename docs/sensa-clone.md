# Clonă dashboard opțiuni (`sensa_server.py`)

UI propriu (fără cod/asset-uri SensaMarket), stdlib `http.server`, zero dependențe noi.
Harta site-ului original: `docs/alphacrunching-map.md`.

## Carduri și surse (toate gratuite)
| Card | Sursă | Cheie / configurare |
|---|---|---|
| Chart (candlestick + volum) | **1day**: Alpha Vantage daily (ultimele ~100 sesiuni); **15m–4h**: doar din cache local | `ALPHAVANTAGE_API_KEY` (gratuit) |
| Top gainers / losers | Cboe delayed quotes (~15 min) | — |
| Sector heatmap | Cboe, ETF-urile SPDR XL* | — |
| Options snapshot: lanț, greeks, C/P ratio, **GEX**, 0DTE | Cboe delayed options | — |
| Short volume | FINRA daily short-sale volume (după închidere) | — |
| Insider trades (Form 4, doar cumpărări/vânzări de piață) | SEC EDGAR | `SEC_CONTACT` = email real (politica SEC) |
| Treasury yield curve | FRED API oficial | `FRED_API_KEY` (gratuit) |
| Market news | Yahoo Finance RSS | — |
| Analyst consensus (opțional) | Finnhub | `FINNHUB_API_KEY`; fără ea cardul arată „n/a" |

Cache TTL: 60 s (cotații, opțiuni, știri), 5 min (insideri), 1 h (FINRA).
Date Cboe/Yahoo: doar uz personal / cercetare. Cheile merg doar în variabile de mediu.

## Graficul candlestick
- **1day** (implicit) merge cu cheia gratuită Alpha Vantage: `TIME_SERIES_DAILY` compact, ~100 sesiuni.
  Se ține 6 h în cache în memorie (cota gratuită e ~25 cereri/zi, 1/s); un eșec se reține 5 min.
- **15m / 30m / 1h / 4h**: endpoint-ul intraday Alpha Vantage este **premium** acum, deci
  `intraday_server.py --backfill-months` nu mai merge cu o cheie gratuită. Aceste timeframe-uri apar
  doar dacă `data/intraday/` (sau `INTRADAY_DATA_DIR`) conține deja bare de 15 min dintr-o altă sursă
  (ex. `massive_loader.py`); altfel cardul spune clar de ce lipsesc.
- Biblioteca `lightweight-charts` v4.2.0 (TradingView, Apache-2.0) este acum build-ul real în
  `markov/intraday/static/` (înainte: stub de 730 de octeți); licența e alături.

## Rulare
```bash
export FRED_API_KEY=...  SEC_CONTACT="you@example.com"   # opțional: FINNHUB_API_KEY, ALPHAVANTAGE_API_KEY (grafic)
python sensa_server.py --watchlist AAPL,MSFT,NVDA,SPY    # http://127.0.0.1:8766
python -m pytest tests -k sensa
```

## Note de acuratețe
- Variația zilnică vine din `price_change_percent` Cboe: `prev_day_close` de la Cboe este ultimul
  close, nu cel dinainte, deci price/prev_close ar arăta ~0%.
- Short volume = ponderea volumului zilei care a fost vânzare short, **nu** short interest
  și **nu** dark pool.
- GEX: convenție calls +, puts −, per 1% mișcare de spot; doar o estimare.

## Ce nu există gratuit / legitim și nu e inclus
- **Prețuri live (WebSocket)**: nu există sursă gratuită; Cboe e oricum întârziat, pagina reîmprospătează la 60 s.
- **Option flow / dark pool real**: fără sursă gratuită bună.
- Cont, watchlist salvat, conectare la brokeri.
