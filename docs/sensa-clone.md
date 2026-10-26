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

## Smart Money: manageri instituționali 13F (`/institutional-investor`)
Pagină proprie de profil de manager, după structura paginii publice a originalului:
`/institutional-investor/manager/<CIK>-<slug>` (antet, 4 statistici, valoare în timp 3Y/5Y/10Y/All,
top holdings, istoric filing-uri cu paginare, alocare, activitate vs trimestrul anterior).
- Date: **SEC EDGAR** (13F-HR, gratuit; necesită `SEC_CONTACT`). Tickere: **OpenFIGI** (CUSIP→ticker, preferă
  listarea US). Valorile dinainte de 2023-01-03 sunt în mii de dolari și se scalează.
- Cifrele coincid cu cele din pagina originală (verificat pe Darsana Capital Partners, CIK 1609098).
- Filing-urile depuse nu se mai schimbă: se țin în cache pe disc în `data/13f/` (ignorat de git).
  Prima deschidere a unui manager e lentă (SEC răspunde în 1–4 s pe cerere; ~40 de cereri pentru 20 de filing-uri), apoi instant.
- Nu există încă: alocarea pe sectoare, compararea a 2 trimestre, filtrele din tabel, logo-uri/fotografii.

## Smart Money: vedere de ansamblu asupra celor mai mari 100 de fonduri (`/smart-money`)
Trei vederi peste **aceleași 100 de fonduri** (cele mai mari după valoarea raportată în 13F), comparate cu trimestrul anterior:
- **Most held**: câte din cele 100 dețin fiecare acțiune (și diferența față de trimestrul trecut), valoare cumulată,
  pondere medie în portofoliile care o dețin, flux activ, câte fonduri au crescut / redus / deschis / închis poziția.
- **Moves**: cumpărări și vânzări active cele mai mari, cele mai multe poziții noi, cele mai multe poziții închise,
  „New to the group" (IPO, spin-off, schimbări de CUSIP) și „Disappeared" (preluări, delistări).
- **Top funds**: clasamentul fondurilor: valoare, variație, poziții, top 3, concentrare top 10, rotație, poziții noi/închise.

Cum se obțin datele (SEC, gratuit): seturile trimestriale **Form 13F data sets** (~100 MB fiecare, se descarcă o dată în
`data/smart_money/zips/`). `python smart_money_build.py` sau butonul **Update from SEC** din pagină (în fundal, cu stare vizibilă).
Prima construcție durează ~3 minute (limita OpenFIGI fără cheie); tickerele se rețin în `data/smart_money/figi.json`.
Serverul verifică zilnic dacă SEC a publicat un trimestru nou (`--smart-hours`), îl construiește singur și trimite
**un rezumat pe Telegram** (cele mai deținute, cumpărări/vânzări active, poziții noi) dacă ai configurat Telegram.

Ce înseamnă cifrele (și ce corectez, ca să nu inducă în eroare):
- **Flux activ** = acțiuni cumpărate/vândute peste creșterea proporțională a fondului (intrările de bani ale fondurilor index),
  la prețul de la sfârșitul trimestrului. **Flux brut** apare în date ca `net_flow`.
- **Split-urile** se detectează (raportul median de acțiuni lipit de un raport uzual, majoritatea fondurilor în jurul lui) și
  se ajustează: altfel un split 10:1 arată ca „92 de fonduri au cumpărat" (22 detectate în Q2 2026).
- **Rotația** se calculează pe ponderi, fără scalarea uniformă a fondului: BlackRock/Vanguard ~2%, casele de tranzacționare 50%+.
- Fluxurile se calculează doar pe fondurile prezente în **ambele** trimestre.
- Limite: 13F conține doar poziții lungi (fără short), cu până la 45 de zile întârziere; valoarea unui fond include și ETF-uri/opțiuni
  în totalul raportat, dar „held" numără doar acțiuni obișnuite (SH, fără PUT/CALL). Salturi mari de la un trimestru la altul la un
  fond (ex. +93%) pot veni din schimbarea structurii depunerii (entități combinate), nu din piață. Amendamentele care doar adaugă
  poziții nu sunt incluse.

## Alerte Smart Money (`/smart-money/alerts`)
Urmărești fonduri după CIK (buton **Follow** pe profilul fondului sau pe pagina de alerte). Când un fond depune un
13F nou, aplicația compară cu trimestrul anterior și creează un **semnal**: poziții noi, ieșite, crescute, reduse
(și amendamentele 13F-HR/A, comparate cu originalul aceleiași perioade). Semnalul apare în pagina de alerte și, dacă
setezi `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID` (vezi `TELEGRAM_SETUP.md`), vine și pe Telegram.
- La prima urmărire istoricul e doar bază de comparație: nu primești alerte pentru filing-uri vechi.
- Verificarea rulează în fundal la `--watch-minutes` (implicit 60) cât timp serverul e pornit, sau manual cu **Check now**.
- Un filing care nu s-a putut descărca se reîncearcă; o notificare eșuată se retrimite; fără duplicate.
- Starea (fonduri urmărite, filing-uri văzute, semnale) e în `data/watch/watch.json` (ignorat de git).
- **13F e trimestrial** (termen: 45 de zile după încheierea trimestrului): semnalul vine când SEC publică filing-ul,
  nu în timp real. Antetele profilului se reîmprospătează singure la 10 minute.
- Cererile care modifică date (POST) cer `Content-Type: application/json` și Host local.

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
