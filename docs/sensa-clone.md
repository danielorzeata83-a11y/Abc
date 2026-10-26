# Clonă dashboard opțiuni (`sensa_server.py`)

UI propriu (fără cod/asset-uri SensaMarket), stdlib `http.server`, zero dependențe noi.
Harta site-ului original: `docs/alphacrunching-map.md`.

## Date (gratuite)
| Widget | Sursă | Note |
|---|---|---|
| Movers | Cboe delayed quotes (`cdn.cboe.com`) | ~15 min întârziere |
| Opțiuni: lanț, greeks, IV, OI, volum, C/P, **GEX / 0DTE** | Cboe delayed options | GEX calculat local din gamma × OI |
| Știri | Yahoo Finance RSS | |
| Curba randamentelor | FRED API oficial | cheie gratuită în `FRED_API_KEY` (fred.stlouisfed.org/docs/api/api_key.html) |
| Consens analiști (opțional) | Finnhub, `FINNHUB_API_KEY` | fără cheie cardul arată „n/a" |

Cache TTL 60 s în `sensa/hub.py`. Date Cboe/Yahoo: doar uz personal / cercetare.

## Rulare
```bash
export FRED_API_KEY=...   # opțional: FINNHUB_API_KEY pentru analiști
python sensa_server.py --watchlist AAPL,MSFT,NVDA,SPY   # http://127.0.0.1:8766
python -m pytest tests -k sensa
```

## Încă lipsesc față de original
Prețuri live (WebSocket), grafic candlestick, heatmap sectoare, option flow / dark pool,
cont/watchlist/brokeri.
