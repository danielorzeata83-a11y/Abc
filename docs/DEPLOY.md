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

## 4. Adu datele reale (backfill DAILY — free tier, 1 apel/simbol)

> **Important:** Alpha Vantage a mutat istoricul **intraday** (`--months`, 15m) la
> endpoint **premium**. Pe cheie free pică imediat. Folosim în schimb istoricul
> **daily**, care e gratis, adânc (20+ ani) și exact granularitatea cerută de motorul
> de validare (orizonturi 1/5/21 zile).

5 simboluri × 1 apel = **5 apeluri**, lejer sub 25/zi. Toate într-o comandă:
```bash
python backfill_cli.py --daily --symbols NVDA,AAPL,MSFT,AMD,TSLA
```
Scriptul se oprește singur dacă lovești limita și **păstrează** ce-a adus (reia mâine).

Datele ajung în `data/intraday/<SIMBOL>_15m.csv` (nume păstrat; conțin bare daily —
pipeline-ul le resamplează la „1day" idempotent). Verifici:
```bash
ls -la data/intraday/
```

> Graficul intraday pe 15m (pasul 6) e separat: cu cheia free poți aduce doar
> ultimele ~30 zile de 15m (sub-proiect ulterior). Validarea nu depinde de el.

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
