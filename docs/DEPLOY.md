# Deploy pe server AWS — grafic intraday + motor de validare (free tier)

> NU este consiliere de investiții. Ghid de operare pentru uz privat.

Rulezi **tu** pașii ăștia pe serverul tău (eu nu am acces la el). Dacă ceva se
blochează, lipește-mi output-ul în chat și depanăm împreună.

Premisă: server Linux cu Python 3 și acces SSH de pe laptopul tău. Cheie Alpha
Vantage **free** (25 apeluri/zi).

---

## 1. Adu codul pe server

```bash
# pe server, in directorul tau de lucru
git clone <URL-ul-repo-ului> Abc          # sau: git pull, daca exista deja
cd Abc
git checkout claude/upbeat-fermi-L3dat     # branch-ul cu tot codul
```

## 2. Mediu Python (o singură dată)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install numpy pandas pytest
python -m pytest -q                        # verificare: trebuie sa fie tot verde
```

## 3. Cheia Alpha Vantage (NU o scrie în cod)

```bash
export ALPHAVANTAGE_API_KEY=cheia_ta_aici
```
(ca să persiste între sesiuni, pune linia în `~/.bashrc` sau folosește un
`EnvironmentFile` de systemd — vezi pasul 7.)

---

## 4. Adu datele reale (backfill eșalonat — free tier 25/zi)

5 simboluri × 12 luni = 60 apeluri, dar ai **25/zi**. Deci împarți pe zile.
Scriptul se oprește singur când lovești limita și **păstrează** ce-a adus.

**Ziua 1** (24 apeluri):
```bash
python backfill_cli.py --symbols NVDA,AAPL --months 12
```
**Ziua 2** (24 apeluri):
```bash
python backfill_cli.py --symbols MSFT,AMD --months 12
```
**Ziua 3** (12 apeluri):
```bash
python backfill_cli.py --symbols TSLA --months 12
```

Datele ajung în `data/intraday/<SIMBOL>_15m.csv`. Verifici:
```bash
ls -la data/intraday/
```

> Vrei mai repede? Cu mai puține luni: `--months 6` → 6 apeluri/simbol → toate 5
> simbolurile într-o zi (30 apeluri… încă peste 25, deci 4 simboluri/zi la 6 luni).
> Pentru validare, **6 luni de daily ≈ 126 bare** — suficient pentru un prim test.

---

## 5. Rulează motorul de validare pe date reale (fără tunel)

De îndată ce ai măcar 1-2 simboluri în cache:
```bash
python validate_cli.py --symbols NVDA,AAPL --data-dir data/intraday --out raport.csv
```
Vezi în terminal tabelul A→E (IC, familii, IC marginal, regim, ansamblu) și un
`raport.csv`. Lipește-mi output-ul aici și **interpretăm împreună** care indicatori
au semnal real și dacă ansamblul bate baseline-ul.

---

## 6. Graficul intraday (are nevoie de fișierul JS real + tunel)

### 6a. Adu build-ul real lightweight-charts (înlocuiește placeholder-ul)
Serverul tău are internet (spre deosebire de mediul în care am dezvoltat eu):
```bash
curl -L -o markov/intraday/static/lightweight-charts.standalone.production.js \
  https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js
```
Verifici că nu mai e placeholder-ul (trebuie să fie zeci de KB, nu 16 linii):
```bash
wc -c markov/intraday/static/lightweight-charts.standalone.production.js
```

### 6b. Pornește serverul (privat, doar pe localhost)
```bash
python intraday_server.py --no-fetch --watchlist NVDA,AAPL,MSFT,AMD,TSLA
```
- `--no-fetch` = servește doar din cache (nu mai cheltuie apeluri AV).
- Ascultă pe `127.0.0.1:8765` — **nu** e expus pe internet. Bine.

### 6c. Tunel SSH de pe laptopul tău (în alt terminal, pe LAPTOP)
```bash
ssh -N -L 8765:127.0.0.1:8765 utilizator@IP-ul-serverului-AWS
```
Apoi deschizi în browserul de pe laptop: **http://localhost:8765**

Vezi lumânări + volum + VWAP + panoul de indicatori, comutabil pe 15m/30m/1h/4h/1zi.

---

## 7. (Opțional) Pornire automată ca serviciu systemd

`/etc/systemd/system/intraday.service`:
```ini
[Unit]
Description=Intraday chart (privat)
After=network.target

[Service]
WorkingDirectory=/home/UTILIZATOR/Abc
Environment=ALPHAVANTAGE_API_KEY=cheia_ta
ExecStart=/home/UTILIZATOR/Abc/.venv/bin/python intraday_server.py --no-fetch
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now intraday
```

---

## Recapitulare rapidă

| Vreau să… | Comanda |
|---|---|
| Aduc date (zilnic, eșalonat) | `python backfill_cli.py --symbols NVDA,AAPL --months 12` |
| Validez indicatori | `python validate_cli.py --symbols NVDA,AAPL --data-dir data/intraday --out raport.csv` |
| Pornesc graficul | `python intraday_server.py --no-fetch` |
| Văd graficul (de pe laptop) | `ssh -N -L 8765:127.0.0.1:8765 user@aws` → http://localhost:8765 |

## Securitate
- Cheia AV doar prin mediu, niciodată în cod sau în git.
- Serverul ascultă doar pe `127.0.0.1` — acces exclusiv prin tunel SSH.
- `data/intraday/` e gitignored — datele nu ajung în repo.
