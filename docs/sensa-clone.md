# Clonă dashboard opțiuni (`sensa_server.py`)

UI propriu (fără cod/asset-uri SensaMarket), stdlib `http.server`, zero dependențe noi.
Harta site-ului original: `docs/alphacrunching-map.md`.

## Date gratuite
| Widget | Sursă | Cheie |
|---|---|---|
| Movers, știri, consens analiști | Finnhub (60 apeluri/min) | `FINNHUB_API_KEY` (finnhub.io/register) |
| Snapshot opțiuni, C/P ratio, greeks | Tradier sandbox (întârziat) | `TRADIER_TOKEN` (developer.tradier.com) |
| Curba randamentelor | home.treasury.gov CSV | nu |

Cache TTL 60 s în `sensa/hub.py` ca să nu se epuizeze limitele gratuite.

## Rulare
```bash
export FINNHUB_API_KEY=... TRADIER_TOKEN=...
python sensa_server.py --watchlist AAPL,MSFT,NVDA,SPY   # http://127.0.0.1:8766
python -m pytest tests -k sensa
```
Hosturile `finnhub.io`, `sandbox.tradier.com`, `home.treasury.gov` trebuie permise în rețea.

## Încă lipsesc față de original
Prețuri live (WebSocket Finnhub nu e în stdlib), grafic candlestick, heatmap sectoare,
GEX 0DTE, option flow / dark pool (nu există surse gratuite bune), cont/watchlist/brokeri.
