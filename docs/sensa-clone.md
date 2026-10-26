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

## Cine deține o acțiune (`/stock/<TICKER>/investors`)
Echivalentul listei „institutional investors" din original (`/api/v1/top-investors/by-ticker/<T>/holdings`).
Pagina: `/stock/PEBO/investors`; API: `/api/investors/PEBO?page=1&limit=20&sortBy=value&sortOrder=desc`
(17 chei de sortare, `limit` max 200, valorile lipsă sunt mereu la coadă).
- **Sursa:** aceleași arhive SEC „Form 13F data sets" folosite la Smart Money. Butonul **Update** construiește în plus
  `holders.db` (SQLite, ~200 MB, ignorat de git) cu pozițiile tuturor filer-ilor din ultimele două trimestre
  (~3,4 M rânduri, ~90 s). Un build eșuat nu înlocuiește indexul bun.
- **Ticker → CUSIP:** OpenFIGI dă numele emitentului, numele se caută în index, iar candidații sunt confirmați prin
  căutarea inversă CUSIP → ticker (cache în `tickers.json`). Fără confirmare, rezultatul este „unknown ticker".
- **Acțiuni în circulație** (pentru `ownershipPct`): SEC `company_tickers.json` + XBRL `dei:EntityCommonStockSharesOutstanding`.
  Companiile cu mai multe clase de acțiuni raportează un număr per clasă, deci procentul lipsește (`null`) în loc să fie greșit.
- **Câmpuri:** shares/value/ownership, `prevShares`, `shareChange(Pct)`, `changeType` (NEW / INCREASED / DECREASED / UNCHANGED / OPTIONS),
  opțiuni call/put (valoarea „net" = call − put, ca în original), `history` pe cele două trimestre, `soldOutCount` în sumar.
- **Verificat pe date reale (Q2 2026, PEBO):** 223 filer-i; call/put/net exact ca în original (472.443 / 410.987 / 61.456).
- **Diferențe față de original:** doar ultimele 2 trimestre (nu 5); „top fund" = primele 100 fonduri după valoarea raportată
  (lista lor e curatoriată), „bank" = lista editabilă `PRIME_BROKER_PATTERNS` din `sensa/investors.py`;
  fără suprapunerea Q3 în curs („current vs carried").

## Lag redus: rapoartele 13F noi, citite direct de pe EDGAR
Arhivele SEC pentru un trimestru apar la săptămâni după ce fondurile încep să depună. `sensa/live13f.py` citește singur
rapoartele noi (`13F-HR`) pentru trimestrul următor:
- **Descoperire:** indexul zilnic EDGAR (`daily-index/<an>/QTR<q>/form.<data>.idx`), apoi pagina de copertă și tabelul de
  poziții al fiecărui raport. Cele mai mari fonduri sunt citite primele; ce a fost citit nu se mai citește.
- **Stocare:** `live13f.db` (SQLite, lângă `holders.db`). Se rulează la pornire și apoi din oră în oră (`--live-hours`, 0 = oprit).
  Cererile sunt spațiate (~3/s) ca să respecte limita SEC. Rapoartele de tip amendament (`13F-HR/A`) sunt sărite.
- **Pagina investitori:** filer-ii care au depus deja folosesc noile poziții (eticheta NEW REPORT, comparate cu trimestrul
  anterior); ceilalți rămân „carried" din ultimul trimestru complet. Sumarul spune câți au raportat deja.
- **Smart Money live:** butonul „Q3 2026 live: N of 100 top funds reported" arată doar fondurile din top 100 care au depus,
  fiecare comparat cu propriul trimestru anterior. Se umple pe măsură ce depun (fondurile mari depun de obicei aproape de termen,
  la 14 noiembrie pentru Q3).
- **Când vine arhiva SEC:** datele live pentru trimestrul acoperit sunt șterse automat, iar vederea completă preia.
- **Stare:** `GET /api/live/status` arată starea și câte rapoarte au fost citite.

## Pagina unei acțiuni (`/stock/<TICKER>`) și legăturile dintre pagini
Orice ticker din aplicație (Smart Money, fonduri, alerte, insideri, dark pool, politicieni, dashboard) e un link către
`/stock/<TICKER>`; căsuța din bara de sus deschide direct orice ticker. Pagina adună, fiecare secțiune independent:
- **Cotație** (Cboe, ~15 min întârziere): preț, variație, minim/maxim, volum, bid/ask, IV 30 zile; **companie** (SEC: nume,
  bursă, industrie, acțiuni în circulație → capitalizare unde numărul e clar).
- **Grafic** (Yahoo Finance, fără cheie și fără cotă zilnică; prioritar față de Alpha Vantage, care rămâne rezervă pentru 1day).
- **Opțiuni** (GEX, put/call, expirare), **analiști** (Finnhub), **știri** (Yahoo RSS), **short volume** (FINRA).
- **Instituții**: primii 8 deținători + „All investors →" (`/stock/<T>/investors`); numele fondurilor duc la pagina fondului.
- **Insideri** (Form 4), **dark pool** (ATS), **politicieni** (House); numele membrilor duc la `/political-trades?member=...`.
- API nou: `/api/quote/<T>`, `/api/company/<T>`. Prima vizită la o acțiune poate dura ~30-60 s (potrivirea ticker → CUSIP prin OpenFIGI,
  apoi rămâne în cache).

## Performanță: portofoliile la prețurile de azi
Prețuri zilnice gratuite (Yahoo Finance, split-ajustate) în `sensa/prices.py`; calculele sunt în `sensa/performance.py`.
- **Fonduri** (`/api/portfolio/<cik>`, cardul „Portfolio at today's prices" pe pagina fondului): pozițiile raportate (cele mai mari 40)
  evaluate la prețul de la sfârșit de trimestru, la data depunerii și azi, cu S&P 500 alături. Contează „de la depunere", adică ce
  puteai copia tu. Se arată cât din valoare a putut fi evaluată.
- **Clasament fonduri** (Smart Money → Performance), **membri House** (Politicians → Performance: randament ponderat al cumpărărilor
  de la data tranzacției și de la data raportării, față de S&P 500), **insideri** (Insiders → Performance: randamentul cumpărărilor
  open-market față de S&P 500, cele mai bune/rele și cele mai mari solduri). Se calculează în fundal la pornire și din 6 în 6 ore
  (`/api/performance/<funds|members|insiders>`; „Compute now" pornește imediat). Prima rulare durează minute.
- **Limite:** buy-and-hold pe poziții raportate (13F nu arată tranzacțiile dintre rapoarte); politicienii raportează intervale, nu
  portofolii (valoare la mijlocul intervalului); soldurile insiderilor apar doar după o reconstruire a datelor Form 4 cu coloana
  „shares owned following". Randamentele insiderilor folosesc aceeași serie ajustată la ambele capete, ca splitul să nu falsifice rezultatul.

## Paginile instituționale (după structura originalului)
- `/institutional-investor`: căutare după CIK, exemple, link la **Latest filings** și la toate literele.
- `/institutional-investor/managers/<literă>` (a–z, `0` = cifre/simboluri): toți cei ~8.800 de declaranți 13F din ultimul trimestru
  publicat în setul SEC, cu total, valoare cumulată, număr mediu de poziții și căutare după nume.
- `/institutional-investor/latest-filings`: cele mai noi rapoarte 13F de pe EDGAR (un rând per manager), cu perioadă, poziții și valoare
  din pagina de copertă (deja apar rapoarte Q3 2026).
- `/institutional-investor/<accession>`: un singur raport: valoare, poziții, fiecare poziție cu modificarea față de trimestrul
  anterior (nou / crescut / redus) și pozițiile închise. Accesiunile se rețin în `data/13f/accessions.json`.
- Observație de date: unii declaranți raportează valoarea în mii de dolari și după 2023, iar setul SEC o păstrează așa;
  cifre ca „$156,245 pentru 104 poziții" sunt erori ale declarantului, nu ale aplicației.

## Insideri (`/inside-trade`)
Tranzacții de piață (cod **P** = cumpărare, **S** = vânzare) din Form 4, din setul trimestrial **Insider Transactions Data Sets** al SEC
(se descarcă o dată în `data/insiders/`; **Update from SEC** sau verificare zilnică). Vederi: cele mai mari cumpărări, cele mai mari vânzări,
**cumpărări în grup** (cel puțin 3 insideri diferiți la aceeași companie), fereastră de 7/30/90 de zile, opțiune de a ascunde vânzările
planificate 10b5-1, căutare după ticker, plus ultimele filing-uri din EDGAR (live, doar câteva zile).
- Granturile, exercitările de opțiuni și cadourile sunt excluse; amendamentele (4/A) la fel.
- Aceeași tranzacție raportată de mai mulți declaranți (declarare comună) se numără o dată; numele se unesc.
- Limită: SEC publică setul trimestrial, deci ultimul trimestru complet e Q3 2026 (până la 30 sept.); octombrie apare doar în feed-ul live.

## Dark pool (`/dark-pool`)
Volum **săptămânal** pe platformele ATS (dark pool) din **FINRA OTC Transparency** (gratuit, fără cheie): cele mai tranzacționate acțiuni
cu variația față de săptămâna anterioară și dimensiunea medie a unei tranzacții, istoric pe 12 săptămâni, cele mai mari platforme, și
defalcarea pe platforme pentru un ticker.
- Ce NU este: prints individuale (acelea sunt date plătite). Este volum agregat, publicat cu ~3 săptămâni întârziere.
- Doar **NMS Tier 1** în totaluri și istoric: FINRA publică Tier 2 cu ~2 săptămâni mai târziu, iar amestecul ar face ultimele
  săptămâni să pară o prăbușire (am prins asta pe date reale).

## Politicieni (`/political-trades`)
Tranzacțiile membrilor **Camerei Reprezentanților** din rapoartele lor „Periodic Transaction Report" (STOCK Act), citite de la
**Clerk of the House** (indexul anual + un PDF per raport; gratuit, fără cheie). Vederi: ultimele tranzacții, cele mai cumpărate,
cele mai vândute, cei mai activi membri; filtre pe fereastră (30–365 de zile), cumpărare/vânzare, ticker și nume.
- PDF-urile se citesc cu **`pypdf`** (Python pur; `pip install -r requirements.txt`), iar dacă lipsește sau nu extrage nimic, cu `pdftotext -raw`.
- Rapoartele se descarcă și se parsează o singură dată (`data/politicians/ptr/`); **Update** sau verificarea zilnică aduc doar rapoartele noi.
- Sumele sunt **intervale** (ex. $1,001–$15,000), deci valorile sunt estimări (mijlocul intervalului; „Over $X" = $X).
- Limite: **doar Camera** (site-ul Senatului cere acceptarea unor termeni într-o sesiune de browser); ~12% dintre rapoarte sunt PDF-uri scanate
  (imagini fără text) și nu pot fi citite fără OCR (apar ca „unreadable"); tranzacțiile datate după propriul raport (greșeli de tastare)
  sunt marcate și excluse din clasamente; rapoartele apar cu până la 45 de zile după tranzacție.

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
