# Smart Lost & Found

A phone-first lost-and-found app. People sign in, report a lost or found item with photos and map pins, rank likely matches, then arrange a public pickup. Finders can stay anonymous.

The app is a React + Vite + TypeScript client in `frontend/` talking to a FastAPI layer in `api/`. Both run locally: the API on port 8000, the web client on port 5173. Matching runs on local Hugging Face models (no API keys).

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

Model weights live in the local Hugging Face cache and are not committed. The first classification or text match also downloads DeBERTa and BGE. Set `LOST_FOUND_MOCK_ML=1` to skip every model (unit tests do this automatically). SQLite and uploaded photos stay under `data/`, which is gitignored.

## Running

Two terminals from the repo root:

```bash
# 1. API on localhost only
source .venv/bin/activate
LOST_FOUND_ALLOW_DEMO_RESET=1 uvicorn api.main:app --host 127.0.0.1 --port 8000

# 2. Web client (Vite proxies /api to the API)
cd frontend && npm run dev -- --host
```

Open `http://localhost:5173`. On a phone on the same Wi-Fi, open `http://<mac-lan-ip>:5173` (`ipconfig getifaddr en0` prints the IP; allow Node through the macOS firewall if prompted). The phone only talks to port 5173.

Offline or fast demo with placeholder scores:

```bash
LOST_FOUND_MOCK_ML=1 LOST_FOUND_ALLOW_DEMO_RESET=1 uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Do not run `uvicorn` with `--reload` or multiple workers during a demo: loaded models live in process memory. The first real request after startup can take minutes while weights load; the Home page shows warmup progress from `GET /api/health`.

### Demo logins

Password is `demo` for every persona. The Account page lists them as one-tap login cards (`GET /api/auth/demo-accounts`).

| Persona | Email | Seeded reports |
|---------|-------|----------------|
| Alex Janssen | `alex@demo.local` | Lost a wallet and AirPods, found keys and a backpack |
| Sam de Vries | `sam@demo.local` | Lost keys and a bottle, found a wallet (anonymous), glasses (anonymous) and a phone |
| Mia Chen | `mia@demo.local` | Lost glasses, found a card holder, AirPods and a bottle |
| Noor Bakker | `noor@demo.local` | Lost a backpack, found a bottle (Amsterdam distractor) |

Every lost item has a matching found report from another persona, photographed separately, so each persona can walk both sides of a pickup. The API seeds accounts and reports on startup without deleting reports you create. "Reload demo" on the Account page (or `python -m scripts.seed_demo_db`) wipes the database and uploads and re-seeds; the HTTP version only works when `LOST_FOUND_ALLOW_DEMO_RESET=1`. See `samples/README.md` for the full pair list.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `LOST_FOUND_DB_PATH` | SQLite file (default `data/lost_found.sqlite`) |
| `LOST_FOUND_MOCK_ML` | `1` skips every model and returns placeholder scores |
| `LOST_FOUND_IMAGE_BACKEND` | Only `dino_lightglue` (the default) is accepted; use `LOST_FOUND_MOCK_ML` for mock |
| `LOST_FOUND_SESSION_SECRET` | Signed-cookie secret; a demo default is used when unset |
| `LOST_FOUND_ALLOW_DEMO_RESET` | `1` enables `POST /api/demo/reset` |

## API summary

Session is a signed cookie (Starlette `SessionMiddleware`); the client sends `credentials: "include"`. Errors are `{ "detail": "..." }`.

- `GET /api/health`, `POST /api/health/warmup`
- `POST /api/auth/register|login|logout`, `GET /api/auth/me` (user includes `avatar` hex color), `GET /api/auth/demo-accounts`
- `GET /api/reports?scope=mine|open`, `POST /api/reports` (multipart), `GET /api/reports/{id}`, `GET /api/reports/{id}/images/{n}`, `PATCH /api/reports/{id}/contact`
- `GET /api/matches?report_id=` (live ranking with component scores and `visual` evidence)
- `GET /api/coordination` (the viewer's active pickup threads), `GET /api/coordination/{lost}/{found}`, `.../messages`, `.../meetup`, `.../meetup/accept|decline`, `.../recovered`
- `GET /api/demo/presets`, `GET /api/demo/presets/{id}/image`, `POST /api/demo/reset`

Photos are served only through `/api/reports/{id}/images/{n}`; filesystem paths never leave the server.

## Architecture

- `frontend/`: React + Vite + TypeScript client (Tailwind, react-leaflet). Routes: `/`, `/account`, `/report`, `/matches`, `/map`, `/pickup`, `/pickup/:lostId/:foundId`.
- `api/`: FastAPI routers, session auth, JSON serializers, and ML warmup status.
- `services/`: classification, text similarity, geo/time scoring, photo matching, match ranking, and the demo seed.
- `database/`: SQLite setup, row conversion helpers, and repository methods.
- `models/schemas.py`: shared dataclasses and enums.
- `samples/`: sample photos and report presets; `scripts/`: model setup, sample cropping, DB reset.
- `utils/config.py`: portable paths and optional environment configuration.

SQLite is implemented with Python's standard library; there is no ORM or migration tool. Core dataclasses are `Report`, `ClassificationResult`, `MatchResult`, `ChatMessage`, `Meetup`, and `User`; enums are `ReportType`, `ReportStatus`, and `MeetupStatus`.

```python
ReportClassifier.classify(description: str) -> ClassificationResult
TextSimilarityService.compare(text_a: str, text_b: str) -> float
GeoMatcher.compare(lost_report: Report, found_report: Report) -> GeoMatchResult
TimeMatcher.compare(lost_report: Report, found_report: Report) -> float
ImageMatcher.compare(lost_images, found_images) -> ImageCompareResult
MatchingEngine.rank_matches(lost_report: Report, found_reports: Iterable[Report]) -> list[MatchResult]
```

## ML pipeline

All models run locally:

- Classification: DeBERTa zero-shot (`MoritzLaurer/deberta-v3-base-zeroshot-v2.0`) for category, urgency, sensitivity, and handling.
- Text: Sentence Transformer `BAAI/bge-small-en-v1.5` cosine similarity between descriptions, calibrated so unrelated items collapse to 0.
- Photos: `rembg` crops the object from the background, DINOv2 ViT-S/14 (`facebook/dinov2-small`) shortlists the top 5 visually similar pairs, then LightGlue + ALIKED (`kornia`) re-ranks them by the number and geometric consistency of feature matches (RANSAC inliers). Photo score = 0.35 × DINOv2 cosine + 0.65 × feature-match score. Pairs outside the shortlist have no photo score.
- Geo/time: Haversine distance with radius decay and exponential time decay.

Overall = weighted blend of text 0.42, photo 0.33, place 0.16, time 0.09. When a pair has no photo score the photo weight is dropped and the rest renormalized, so a missing photo is never a 0% photo score. A category mismatch is a hard gate to 0. If the vision stack cannot load, photo scores are `null` with an `image_error` explaining why and ranking continues on description, place, and time.

## Tests

```bash
LOST_FOUND_MOCK_ML=1 python -m pytest -q          # unit + FastAPI contract tests
RUN_REAL_ML=1 python -m pytest -q tests/test_real_ml.py   # real-model checks (downloads weights)
cd frontend && npm run build                       # type-check + production build
python scripts/setup_vision.py                     # proves the photo models load
```

Unit tests force `LOST_FOUND_MOCK_ML=1` and do not prove the real models work.

## Known limitations (hackathon scope)

One SQLite file and one upload directory on local disk; one Uvicorn worker; demo session secret; no CSRF protection; demo reset wipes the database; first real-model use downloads weights and can take minutes; sample image redistribution rights are unverified (see `samples/README.md`).
