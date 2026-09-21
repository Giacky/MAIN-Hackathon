# Smart Lost & Found

A small, runnable foundation for a three-person hackathon project. Users can submit lost/found reports and navigate mock matches, map, chat, drop-off, and recovery experiences. The ML and recovery features are intentionally interfaces or placeholders.

## Setup

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\Activate.ps1    # Windows PowerShell
pip install -r requirements.txt
streamlit run app.py
```

No model download, API key, or environment variable is required. Runtime SQLite files and uploads are ignored by Git.

## Architecture

- `app.py`: application bootstrap and navigation only.
- `pages/`: Streamlit screens and forms.
- `components/`: reusable display components for reports and matches.
- `services/`: stable ML/matching interfaces with lightweight mock behavior.
- `database/`: SQLite setup, row conversion helpers, and repository methods.
- `models/schemas.py`: shared data contracts used by every workstream.
- `utils/config.py`: portable paths and optional environment configuration.

SQLite is implemented with Python's standard library, so SQLAlchemy is unnecessary. The default database is `data/lost_found.sqlite`; set `LOST_FOUND_DB_PATH` later if a different location is needed. Local disk on Streamlit Community Cloud is ephemeral, so upload/database storage should be swapped for persistent storage before relying on it.

## Team development

### Files/folders owned by Developer 1 — Frontend/UI

- `pages/`
- `components/`

Build the report and upload experience, maps, match cards, recovery/drop-off UI, chat UI, and visual polish. Mock objects in `pages/matches.py` let this work proceed without ML or database changes.

### Files/folders owned by Developer 2 — ML/Matching

- `services/`

Replace the explicit mock implementations for classification, text similarity, location, time, optional image similarity, and score aggregation. Keep the public signatures stable.

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

## Future ML

These are documented targets, not current dependencies:

- DeBERTa: `MoritzLaurer/deberta-v3-base-zeroshot-v2.0` for zero-shot category, urgency, sensitivity, and handling classification.
- Sentence Transformer: `BAAI/bge-small-en-v1.5` (or equivalent) for semantic lost/found description similarity.
- Optional DINOv2, SigLIP, or CLIP embeddings for image similarity if time permits.

Add PyTorch, Transformers, Sentence Transformers, or imaging packages only when their implementations land.
