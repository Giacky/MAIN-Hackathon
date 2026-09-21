# Smart Lost & Found

A small, runnable foundation for a three-person hackathon project. Users can submit lost/found reports; the Mac demo server classifies descriptions, stores optional photos, and ranks matches. Chat and map are still placeholders.

## Setup

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\Activate.ps1    # Windows PowerShell
pip install -r requirements.txt
streamlit run app.py
```

The first real classification or match ranking downloads Hugging Face weights onto this machine (DeBERTa + BGE + CLIP). Set `LOST_FOUND_MOCK_ML=1` to skip models (tests do this automatically). Runtime SQLite files and uploads are ignored by Git.

### Demo server (MacBook + phone)

`.streamlit/config.toml` binds Streamlit to all interfaces on port 8501. On the M2 Pro:

```bash
source .venv/bin/activate
streamlit run app.py
```

On a phone on the same Wi-Fi, open `http://<mac-lan-ip>:8501`. Allow Python through the macOS firewall if the phone cannot connect. Inference uses Apple MPS when available.

To find the Mac LAN IP:

```bash
ipconfig getifaddr en0
```

## Architecture

- `app.py`: application bootstrap and navigation only.
- `pages/`: Streamlit screens and forms.
- `components/`: reusable display components for reports and matches.
- `services/`: classification, text similarity, geo/time scoring, and match ranking.
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

## Running and smoke tests

```bash
streamlit run app.py
python -m unittest discover -s tests
```

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
- CLIP: `clip-ViT-B-32` for photo similarity when both reports have saved images.
- Geo/time: Haversine + radius decay and exponential time decay (not neural nets).

Unittests set `LOST_FOUND_MOCK_ML=1` so they never download weights.
