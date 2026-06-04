# CLI-uri — index

Toate poartă „NU este consiliere de investiții". Zero dependențe în afară de
numpy/pandas. Cheile API se iau din mediu, niciodată hardcodate.

## Date (cache)

### `backfill_cli.py` — populează cache-ul daily
```
python backfill_cli.py --source stooq --daily --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday
```
Surse fără cheie: `stooq`, `yahoo` (istoric adânc, 1 apel/simbol). `twelvedata`
cu `TWELVEDATA_API_KEY`. Scrie `Bars` per simbol în `--data-dir`.

## Validare indicatori (motorul A→E)

### `validate_cli.py` — TIER 1 / TIER 2 / all pe watchlist (din cache)
```
python validate_cli.py --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday --indicators tier2
```
`--indicators tier1|tier2|all`. Rulează A→E (IC pooled, familii, IC marginal,
IC pe regim, ansamblu) pe simbolurile din cache. `--target return|vol`. `--out` → CSV.

### `validate_universe_cli.py` — TIER 2 time-series pooled pe univers larg
```
python validate_universe_cli.py --universe data/sp500.csv --indicators tier2
```
Construiește un cache temporar din panel-ul long (date, ohlcv, Name) și rulează
același motor A→E peste sute de simboluri. Pooling-ul scoate la iveală semnale slabe
(ex: `ts_reversal`) invizibile pe câteva nume.

### `validate_xs_cli.py` — TIER 2b factori cross-secționali + blend
```
python validate_xs_cli.py --universe data/sp500.csv          # CSV (2013-18)
python validate_xs_cli.py --cache-dir data/intraday          # istoric lung din cache
```
Long-short pe univers (momentum, reversal, low_vol, resmom, amihud), **net de costuri**:
Sharpe full/OOS + p-value sign-flip per factor, apoi **blend sign-aware** (ponderi ∝
Sharpe in-sample, conviction). `--split` fracția in-sample, `--no-blend` sare peste blend.
Cu `--cache-dir` construiește panel-ul din cache-ul daily (fereastră comună, toate
numele) — istoric mai adânc decât CSV-ul Kaggle. `--symbols` restrânge universul.

## Cross-asset & raportare

### `crossasset_cli.py` — rețea lead-lag (transfer entropy)
```
python crossasset_cli.py --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday
```
Cine conduce pe cine (TE(i→j) între toate perechile), clasament lider→urmăritor.

### `engine_alert_cli.py` — raport zilnic → Telegram
```
python engine_alert_cli.py --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday --dry-run
```
Prognoză de volatilitate per simbol (z realized_var) + lead-lag, cu freshness și
disclaimer. `--dry-run` previzualizează; fără el trimite (cere `TELEGRAM_TOKEN` +
`TELEGRAM_CHAT_ID` din mediu sau `--token/--chat-id`). `--asof` pentru dată fixă.

### `tradingview_cli.py` — trading view HTML self-contained
```
python tradingview_cli.py --symbols NVDA,AAPL,MSFT,AMD,TSLA --data-dir data/intraday --out results/tv.html
```
Pagină HTML offline (zero deps externe): lumânări OHLC + volum + sub-panou cu
semnalul de volatilitate (z realized_var), taburi de simboluri, crosshair la hover.
`--max-bars` câte bare recente, `--asof` dată fixă.

## Rezultate

- `results/TIER2_FINDINGS.md` — sinteza onestă a testelor TIER 2 / 2b.
- `results/REPORT.md` — verdictul general al proiectului.
