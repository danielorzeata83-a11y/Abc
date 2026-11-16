# alphacrunching.sensamarket.com/dashboard — hartă surse de date și legături

Analiză pasivă (HTML + chunk-uri JS publice, 26.10.2026). Nu s-au apelat API-uri
autentificate și nu s-a făcut login. Domeniul `alphacrunching.*` este un
white-label/partener al **SensaMarket** (`og:url` = `www.sensamarket.com/dashboard`).

## Stack front-end
- Next.js (App Router, Turbopack, RSC), React, Redux Toolkit + redux-saga, axios, moment.
- Grafice: **TradingView Charting Library** (self-hosted) + **ECharts** (heatmap/treemap, sparkline).
- i18n: `next-intl`. Temă dark/light (cookie `sensa-theme`).
- Hosting/CDN: Cloudflare. Analytics: Google Tag Manager `GTM-P82L72CH`.
- Anti-bot la auth: Cloudflare Turnstile.
- Plăți: Stripe (apel `POST /api/v1/payment/create-subscription-payment`).
- White-label: logo partener per subdomeniu din `cdn.sensamarket.com/partners_logo/<partener>.png`.

## Backend-uri (de unde vin datele)

| Host | Rol | Folosit pentru |
|---|---|---|
| `https://market.optionar.com` (`NEXT_PUBLIC_API_BASE_URL`) | API principal de piață | `/api/v1/market/news`, `/api/v1/company/analyst-rating/{sym}`, `/api/v1/ticker/{sym}`, `/api/v1/ticker/search/{q}`, `/api/v1/gex/0dte/history?symbol=`, `/api/v1/gex/0dte/premium-drift?symbol=` |
| `https://market.sensamarket.com/api` | alias/instanță a aceluiași API; axios cu token `tradestation_access_token` din localStorage | cotații/lanț prin TradeStation |
| `https://institution.sensamarket.com` (`NEXT_PUBLIC_INSTITUTION_API_URL`) | API „instituțional" + cookie auth (`sensa_auth_token_v3`) | `/api/v1/movers`, `/movers/sectors`, `/heatmap`, `/sector`, `/sector-heatmap`, `/screener`, `/greeks-analytics`, `/greeks-analytics/indices-drift`, `/api/v1/brokerage/*` (header `X-Broker-Token`) |
| același host (`/api/v1/...`) | date proprii utilizator | auth (`login`, `google-login`, `sign-up`, `validate-otp-and-register-user`, `forgot-password`, `resend-otp`), `user/me`, `watchlist/get-all-watchlists` (+ create/delete), `signal/get-signals`, `options/saved-filters` (CRUD + apply), `options/option-activity/{flow,summary,leaderboards,ratios}`, `news-letter/subscribe` |
| `wss://stream.sensamarket.com/ws?userId=<_sid>` (`NEXT_PUBLIC_WS_URL`) | streaming prețuri | vezi protocol mai jos |
| `https://tv.sensamarket.com` | `charting_library/` + `datafeeds/udf/dist/bundle.js` | datafeed UDF pentru TradingView |
| `https://cdn.sensamarket.com` | imagini/logo-uri | static |

### Protocol WebSocket
- Conectare: `wss://stream.sensamarket.com/ws?userId=<localStorage._sid | "anonymous">`
- Client → server: `{"action":"subscribe"|"unsubscribe","symbols":["AAPL",...],"eventTypes":["agg"]}`
- Server → client: `{"type":"market_event","payload":{"type":"agg","symbol","startTime","open","high","low","close","volume","accumulatedVolume"|"av"}}`
- Indicii sunt prefixați `I:` (ex. `I:SPX`). Reconnect cu backoff 1s → 30s.

### Brokeri (OAuth, link-out)
- **Tradier**: `api.tradier.com/v1/oauth/authorize`, onboarding `onboarding.tradier.com`, `trade.tradier.com/sensamarket/`.
- **TradeStation**: `signin.tradestation.com/authorize`, audience `api.tradestation.com`, redirect `www.sensamarket.com/brokerage/connect/tradestation`.
- (Client ID-urile sunt hardcodate în JS-ul lor; sunt ale lor — **nu se refolosesc**.)

### Terți
Google Sign-In (`accounts.google.com`), YouTube (embed „latest videos"), TradingView `s3.tradingview.com/tv.js` (widget-uri), Medium/X/LinkedIn/IG/FB/Pinterest (footer).

## Rute / pagini
`/dashboard`, `/trade`, `/trade/<sym>`, `/greeks-analytics` (+`/indices-drift`), `/screener`, `/sector-heatmap`, `/dark-pool`, `/inside-trade`, `/political-trades`, `/institutional-investor`, `/cashflow`, `/calendar`, `/strategies`, `/paper-trading`, `/save-trade`, `/community`, `/sensa-pulse`, `/sensa-learn`, `/brokers`, `/brokerage`, `/pricing`, `/login`, `/signup`, `/profile`.

## Widget-uri dashboard (după module CSS)
ticker-bar, index-cards-row (+sparkline), movers / movers-widget, sector-heatmap-widget (treemap), watchlist-card, news-card, fear-greed-dashboard (gauge), treasury-yield-curve, cp-ratio-widget, options-snapshot, analyst-consensus, shorts-card, latest-videos-card, quick-actions-card, stock-key-stats/stock-metrics, chart-workspace (detașabil), global-search (⌘K), widget-picker.

## Ce NU se poate afla din front-end
- **Furnizorul upstream real** (vendor de market data / opțiuni / dark-pool / insider). Formatul (`published_utc`, prefix `I:`, evenimente `agg`) seamănă cu stilul Polygon/Massive, dar e doar o presupunere — JS-ul nu o confirmă.
- Logica server (calcul GEX, semnale, flow, scoruri), baza de date, schema reală a răspunsurilor.
- Majoritatea datelor sunt în spatele autentificării/abonamentului (`pro-lock-card`, plan FREE vs plătit).

## Pentru clonă
Clonarea 1:1 a codului/asset-urilor lor (JS/CSS/logo/charting library TradingView licențiată) nu e ok: sunt proprietare. Varianta corectă: UI propriu cu aceleași pagini/widget-uri și un backend propriu alimentat de un furnizor licențiat (ex. Polygon/Massive, Tradier, Finnhub, FMP), cu același contract REST + WS descris mai sus.
