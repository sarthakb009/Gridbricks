# Northstar Wind Desk

A day-ahead wind intelligence workspace for a GB electricity buyer. It freezes a national wind forecast at a configurable decision cutoff, joins it to eventual wind outturn, and quantifies forecast error across half-hourly settlement periods.

## Run locally with Docker

```bash
docker compose up --build
```

Open [http://localhost:5173](http://localhost:5173). The FastAPI service is at [http://localhost:8000](http://localhost:8000) (API docs at `/docs`). The app retrieves January 2026 data directly from the Elexon Insights API; internet access is required from the backend container. Choose any January delivery date and a day-ahead cutoff in UK local time. The initial default is 15 January at a 10:00 UK cutoff on the previous day; the cutoff is a configurable decision assumption for this prototype, not a claim about a client's actual gate-closure process.

## What the product does

- Presents the frozen forecast vintage available before the selected decision cutoff.
- Joins WINDFOR forecasts and FUELHH actuals by `startTime` at half-hourly resolution.
- Shows forecast vs actual, signed error by period, and CSV export.
- Calculates MAE (MW), RMSE (MW), WAPE (% of actual wind volume), and mean bias (MW; positive means over-forecast).
- Gives the buyer a clear view of forecast uncertainty to inform residual procurement planning. It does not calculate consumer demand, thermal dispatch, market prices, or a recommended purchase volume because those inputs are outside the requested Elexon-only scope.

## Design and implementation review

**Architecture.** React/Vite provides the decision dashboard and Recharts visualisations. FastAPI owns Elexon access, date/cutoff handling, forecast-vintage selection, same-period matching, and metrics. Docker Compose runs both services. The source datasets are solely Elexon's WINDFOR and FUELHH. No API key is required by this prototype. The UI presents missing actuals as gaps rather than imputing them.

**Vintage semantics.** For a selected delivery day, the API requests the 48 target settlement periods in WINDFOR and FUELHH and restricts WINDFOR publication times to a four-day lookback ending at the configured cutoff (previous-day cutoff, Europe/London by default). For each target `startTime`, it retains the latest `publishTime` not later than cutoff. This period-level selection handles revised forecast runs and makes the snapshot reproducible. The cutoff should be set to the buyer's actual auction decision deadline before production use.

**Metric definitions.** For matched periods, error is forecast − actual. MAE = mean absolute error, RMSE = square root of mean squared error, WAPE = sum absolute error / sum actual × 100, and bias = mean signed error. WAPE is omitted when actual wind volume is zero; metrics are omitted when no actuals have arrived. This prototype evaluates the selected day-ahead vintage retrospectively against the outturn. It is not a calibrated probabilistic forecast or a procurement optimiser.

**Operational considerations.** The API returns a clear error when Elexon is unavailable or the selected forecast vintage is absent. For production, add upstream caching/retry policy, request throttling, observability, data completeness controls, authentication, and persistent snapshots. Elexon API query limits and returned schema should be checked against the live API before operational deployment.

## Client pitch

**Northstar makes the wind decision auditable.** At the moment a buyer is making a day-ahead call, the desk can see the latest Elexon wind forecast that was actually available by its cutoff, rather than a forecast revised later. The forecast is set beside what the system delivered, with the miss shown at each half-hour and summarised in MW and percent. That gives the team a practical uncertainty signal for residual procurement conversations, while keeping the source, time, and calculation visible. Start with a historical January 2026 review, agree the desk's true cutoff, then extend into a live daily workflow with client demand and portfolio data if desired.

## Files and directories

- `backend/main.py` — FastAPI routes, Elexon fetches, period matching, and accuracy metrics.
- `backend/requirements.txt` and `backend/Dockerfile` — Python service dependencies and image.
- `frontend/src/main.jsx` — React page, API request, chart/table components, and CSV export.
- `frontend/src/style.css` — dashboard styles; `frontend/index.html` — Vite page shell.
- `frontend/package.json` and `frontend/Dockerfile` — npm scripts, dependencies, and image.
- `video/northstar-wind-desk-demo.mp4` — two-part, caption-led demo (6.92 minutes total).
- `video/northstar-wind-desk-demo.srt` — matching timed transcript; `video/source/` — narration and build script.
- `CLIENT_PITCH.md` — client-facing pitch and demo flow.
- `docker-compose.yml` — local frontend/backend orchestration.
- `vercel.toml` — Vercel full-stack service configuration for the Vite frontend and FastAPI backend.
- `.gitignore` — excludes generated dependencies, frontend build output, and intermediate video renders.

## Submission links

- Demo video: `video/northstar-wind-desk-demo.mp4` (caption-led guide, 6.92 minutes total; part 1 is 3.10 minutes and part 2 is 3.81 minutes).
- Deployed application: [Northstar Wind Desk](https://northstar-wind-desk.vercel.app) (public Vercel deployment).
- Public GitHub repository: [sarthakb009/Gridbricks](https://github.com/sarthakb009/Gridbricks).

## Data sources

- [FUELHH stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) — half-hourly generation by fuel type, filtered to WIND.
- [WINDFOR stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) — forecast generation with target `startTime` and publication `publishTime`.
- API base: `https://data.elexon.co.uk/bmrs/api/v1`.

Contains BMRS data © Elexon Limited.

## Deployment

The app is deployed at [northstar-wind-desk.vercel.app](https://northstar-wind-desk.vercel.app). The root `vercel.toml` defines the Vite frontend and FastAPI backend as Vercel services; `/api/*` routes to FastAPI before the frontend catch-all. GitHub `main` is connected for automatic deployments. The backend Dockerfile also supports deployment on Heroku or another container host. See [Vercel Python runtime documentation](https://vercel.com/changelog/python-on-vercel-is-now-generally-available) for the service layout.

## AI assistance

AI tools were used to help with domain/API research, product framing, and implementation of the prototype, including this README.
