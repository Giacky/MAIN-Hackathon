# Smart Lost & Found

A phone-first lost-and-found app for a three-person hackathon. People sign in, report a lost or found item (with optional photos and map pins), rank likely matches, then arrange a public pickup. Finders can stay anonymous.

The user-facing app is a React + Vite + TypeScript client in `frontend/` talking to a small FastAPI layer in `api/`. Both sit on the same Python domain, SQLite persistence, and local ML that the original Streamlit app (`app.py`) still uses. Streamlit is kept as a fallback.

## Setup

Python 3.11 or newer and Node 20 or newer.

```bash
git clone https://github.com/Giacky/MAIN-Hackathon.git
cd MAIN-Hackathon
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\Activate.ps1    # Windows PowerShell
pip install -r requirements.txt
python scripts/setup_vision.py  # downloads DINOv2, ALIKED, LightGlue, rembg (optional; see mock mode)
cd frontend && npm install && cd ..
```

Model weights are cached in the local Hugging Face cache and do not belong in Git. The first classification or text match also downloads DeBERTa and BGE. Set `LOST_FOUND_MOCK_ML=1` to skip every model (unit tests do this automatically). Runtime SQLite files and uploads stay on disk and are gitignored; do not delete `data/` if you want to keep existing reports and photos.

## Running the React app (recommended)

Two terminals from the repo root:

```bash
# 1. API on localhost only
source .venv/bin/activate
LOST_FOUND_ALLOW_DEMO_RESET=1 uvicorn api.main:app --host 127.0.0.1 --port 8000

# 2. Web client (Vite proxies /api to the API)
cd frontend && npm run dev -- --host
```

Open `http://localhost:5173`. On a phone on the same Wi-Fi, open `http://<mac-lan-ip>:5173` (`ipconfig getifaddr en0` prints the IP; allow Node through the macOS firewall if prompted). The phone only talks to port 5173.

Demo logins (password `demo` for all three): Alex `alex@demo.local` (lost wallet, lost AirPods), Sam `sam@demo.local` (found wallet, stays anonymous), Mia `mia@demo.local` (found card holder, found AirPods). The API seeds these on startup without deleting reports you create. The "Reload demo" control on the Account page wipes the database and re-seeds; it only works when `LOST_FOUND_ALLOW_DEMO_RESET=1`.

Offline / fast demo with placeholder scores:

```bash
LOST_FOUND_MOCK_ML=1 LOST_FOUND_ALLOW_DEMO_RESET=1 uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Do not run `uvicorn` with `--reload` or multiple workers during a demo: loaded models live in process memory. The first real request after startup can take minutes while weights load; the Home page shows warmup progress from `GET /api/health`.

Environment variables: `LOST_FOUND_DB_PATH` (SQLite file), `LOST_FOUND_MOCK_ML`, `LOST_FOUND_IMAGE_BACKEND` (`dino_lightglue` default, or `clip`), `LOST_FOUND_SESSION_SECRET` (signed cookie secret; a demo default is used), `LOST_FOUND_ALLOW_DEMO_RESET`.

### API summary

Session is a signed cookie (Starlette `SessionMiddleware`); the client sends `credentials: "include"`. Errors are `{ "detail": "..." }`.

- `GET /api/health`, `POST /api/health/warmup`
- `POST /api/auth/register|login|logout`, `GET /api/auth/me`
- `GET /api/reports?scope=mine|open`, `POST /api/reports` (multipart), `GET /api/reports/{id}`, `GET /api/reports/{id}/images/{n}`, `PATCH /api/reports/{id}/contact`
- `GET /api/matches?report_id=` (live ranking with component scores and `visual` evidence)
- `GET /api/coordination/{lost}/{found}`, `.../messages`, `.../meetup`, `.../meetup/accept|decline`, `.../recovered`
- `GET /api/demo/presets`, `POST /api/demo/reset`

Photos are served only through `/api/reports/{id}/images/{n}`; filesystem paths never leave the server.

### Streamlit fallback

`.streamlit/config.toml` binds Streamlit to all interfaces on port 8501:

```bash
source .venv/bin/activate
streamlit run app.py
```

Open `http://<mac-lan-ip>:8501` on the phone. Run either the API or Streamlit against `data/lost_found.sqlite`, not both at once. Note that Streamlit's boot still prunes non-demo reports; the API does not.

To find the Mac LAN IP:

```bash
ipconfig getifaddr en0
```

## Architecture

- `frontend/`: React + Vite + TypeScript client (Tailwind, react-leaflet). Routes: `/`, `/account`, `/report`, `/matches`, `/map`, `/pickup/:lostId/:foundId`.
- `api/`: FastAPI routers, session auth, JSON serializers, and ML warmup status.
- `app.py`, `pages/`, `components/`: the Streamlit fallback UI.
- `services/`: classification, text similarity, geo/time scoring, photo matching, and match ranking.
- `database/`: SQLite setup, row conversion helpers, and repository methods.
- `models/schemas.py`: shared data contracts used by every workstream.
- `utils/config.py`: portable paths and optional environment configuration.

SQLite is implemented with Python's standard library, so SQLAlchemy is unnecessary. The default database is `data/lost_found.sqlite`; set `LOST_FOUND_DB_PATH` later if a different location is needed. Local disk on Streamlit Community Cloud is ephemeral, so upload/database storage should be swapped for persistent storage before relying on it.

## Team development

### Files/folders owned by Developer 1 — Frontend/UI

- `pages/`
- `components/`

Build the report and upload experience, maps, match cards, recovery/drop-off UI, chat UI, and visual polish. Matches are ranked live from SQLite via `MatchingEngine`.

### Files/folders owned by Developer 2 — ML/Matching

- `services/`

Classification, text similarity, geo/time scoring, CLIP image similarity, and score aggregation live here. Keep the public signatures stable. Mock mode via `LOST_FOUND_MOCK_ML=1`.

### Files/folders owned by Developer 3 — Data/Recovery/Integration

- `database/`

Extend persistence for reports, generated matches, chat messages, drop-offs, and recovery state. Connect durable upload storage when selected for deployment.

### Shared files — modify carefully

- `models/schemas.py` (the cross-team contract; coordinate every change)
- `app.py` (navigation/bootstrap)
- `utils/config.py`
- `requirements.txt`
- `README.md`
- `.gitignore`

Avoid changing shared contracts without coordinating with the other developers. Prefer adding implementation behind an existing interface.

## Shared interfaces

Core dataclasses are `Report`, `ClassificationResult`, `MatchResult`, `ChatMessage`, and `DropOff`; enums are `ReportType` and `ReportStatus`.

```python
ReportClassifier.classify(description: str) -> ClassificationResult
TextSimilarityService.compare(text_a: str, text_b: str) -> float
GeoMatcher.compare(lost_report: Report, found_report: Report) -> GeoMatchResult
TimeMatcher.compare(lost_report: Report, found_report: Report) -> float
ImageMatcher.compare(lost_images, found_images) -> float | None
MatchingEngine.rank_matches(lost_report: Report, found_reports: Iterable[Report]) -> list[MatchResult]
```

`ReportRepository` documents the persistence boundary, while `SQLiteRepository` provides the initial implementation.

## Tests

```bash
LOST_FOUND_MOCK_ML=1 python -m unittest discover -s tests   # includes tests/test_api.py
cd frontend && npm run build                                 # type-check + production build
python scripts/setup_vision.py                               # proves the real photo models load
```

Unit tests force `LOST_FOUND_MOCK_ML=1` and do not prove the real models work.

## Deployment

The simplest website path is Streamlit Community Cloud:

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create an app from the repository.
3. Select `app.py` as the entry point and deploy.
4. Add future secrets in the Cloud secrets UI using `.streamlit/secrets.toml.example` as a guide; never commit `secrets.toml`.

The current app needs no secrets. For durable public usage, replace local SQLite/upload storage because Community Cloud instances can restart and discard local runtime data.

## Matching models

Implemented locally (no API key):

- DeBERTa: `MoritzLaurer/deberta-v3-base-zeroshot-v2.0` for category, urgency, sensitivity, and handling.
- Sentence Transformer: `BAAI/bge-small-en-v1.5` for lost/found description similarity.
- Photos: `rembg` crops the object from the background, DINOv2 ViT-S/14 (`facebook/dinov2-small`) shortlists the top 5 visually similar pairs, then LightGlue + ALIKED (`kornia`) re-ranks them by the number and geometric consistency of feature matches (RANSAC inliers). Photo score = 0.35 × DINOv2 cosine + 0.65 × feature-match score. Pairs outside the shortlist are ranked on description, place, and time only. CLIP (`clip-ViT-B-32`) is the automatic fallback if the vision stack cannot load.
- Geo/time: Haversine + radius decay and exponential time decay (not neural nets).

Overall = weighted blend of text 0.42, photo 0.33, place 0.16, time 0.09 (photo weight is dropped and renormalized when no photo score exists), then a hard category gate. Unittests set `LOST_FOUND_MOCK_ML=1` so they never download weights.

## Known limitations (hackathon scope)

One SQLite file and one upload directory on local disk; one Uvicorn worker; demo session secret; no CSRF protection; demo reset wipes the database; first real-model use downloads weights and can take minutes; sample image redistribution rights are unverified (see `samples/README.md`).
