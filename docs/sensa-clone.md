# Clonă dashboard opțiuni (`sensa_server.py`)

UI propriu (fără cod/asset-uri SensaMarket), stdlib `http.server`, zero dependențe noi.
Harta site-ului original: `docs/alphacrunching-map.md`.

## Carduri și surse (toate gratuite)
| Card | Sursă | Cheie / configurare |
|---|---|---|
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

## Rulare
```bash
export FRED_API_KEY=...  SEC_CONTACT="you@example.com"   # opțional: FINNHUB_API_KEY
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
- **Grafic candlestick**: singura sursă gratuită fără cheie de istoric (Yahoo `chart`) este neoficială.
  În repo există deja `intraday_server.py` (candlestick + VWAP, `lightweight-charts`, Alpha Vantage);
  poate fi legat aici dacă se dorește.
- Cont, watchlist salvat, conectare la brokeri.
