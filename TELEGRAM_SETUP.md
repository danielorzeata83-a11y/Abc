# Alerte zilnice pe Telegram (gratis, fără server propriu)

GitHub rulează un mic robot o dată pe zi care îți trimite pe telefon termometrul
CAPE + candidații CHEAP+QUALITY ai screener-ului. Tu nu ții nimic pornit.

> Artefact de cercetare. **NU este consiliere de investiții.**

## 1. Creează botul (o singură dată)
1. În Telegram, deschide **@BotFather** (cel cu bifă albastră ✓).
2. `/newbot` → nume → username terminat în `bot` → copiezi **TOKEN-ul**.

## 2. Află-ți chat_id (o singură dată)
1. Scrie orice botului tău (ex: `salut`).
2. Pe PC, în folderul proiectului:
   ```
   python telegram_chatid.py --token TOKEN_TAU
   ```
   → îți afișează `chat_id = ...`

## 3. Pune-le ca secrete în GitHub (o singură dată)
Repo pe GitHub → **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
|---|---|
| `TELEGRAM_TOKEN` | token-ul de la BotFather |
| `TELEGRAM_CHAT_ID` | chat_id-ul de la pasul 2 |

Secretele sunt criptate — nu apar niciodată în cod sau în loguri.

## 4. Testează acum (fără să aștepți dimineața)
Repo pe GitHub → tab **Actions** → workflow **Daily Telegram alert** →
**Run workflow**. Ar trebui să-ți pice mesajul pe Telegram în ~1 minut.

## Cum funcționează
- Rulează automat **06:00 UTC, luni–vineri** (≈09:00 RO vara, 08:00 iarna).
  Schimbi ora în `.github/workflows/daily-alert.yml` (linia `cron:`).
- Pleacă de la datele „seed" din `ci_data/` (merge mereu), apoi încearcă să
  aducă prețurile de azi prin yfinance; dacă yfinance e capricios, folosește seed-ul.
- Datele CAPE (Shiller) se mișcă lent; reîmprospătează din când în când
  `ci_data/sp500_monthly.csv` (sursă: multpl.com/shiller-pe).

## Alertă „be greedy" (piața devine ieftină)
Când CAPE coboară sub un prag, mesajul primește sus un banner proeminent
`>>> PIATA A DEVENIT IEFTINA <<<` (și mai puternic sub 15, nivel rar istoric).
Două praguri configurabile:
- **Prag 1 — „piața a devenit ieftină"** (implicit **22**): secret opțional
  `CHEAP_CAPE_THRESHOLD` sau `--cheap-threshold 22` local.
- **Prag 2 — „CUMPĂRĂ AGRESIV"** (implicit **15**, rar istoric): secret opțional
  `AGGRESSIVE_CAPE_THRESHOLD` sau `--aggressive-threshold 15` local.
- Acum (CAPE ~30.8) ambele sunt dormante; se trezesc singure la o corecție reală.

## Test local (opțional)
```
python telegram_alert.py --dry-run      # vezi mesajul, fără să trimiți
python telegram_alert.py                # trimite (necesită TELEGRAM_TOKEN + TELEGRAM_CHAT_ID în mediu)
```
