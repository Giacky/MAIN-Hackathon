"""Demo presets for quick form fill and match seeding."""

from pathlib import Path

from utils.config import PROJECT_ROOT

SAMPLES_DIR = PROJECT_ROOT / "samples" / "images"

PRESETS: dict[str, dict] = {
    "lost_wallet": {
        "label": "Lost wallet",
        "report_type": "lost",
        "description": (
            "Small black leather wallet with a blue bank card and student ID inside. "
            "Lost near the university library."
        ),
        "latitude": 50.8514,
        "longitude": 5.6900,
        "radius_meters": 500,
        "image": SAMPLES_DIR / "lost_black_wallet.png",
    },
    "found_wallet": {
        "label": "Found wallet (match)",
        "report_type": "found",
        "description": (
            "Black wallet found by the university library entrance. "
            "Contains cards and looks like leather."
        ),
        "latitude": 50.8516,
        "longitude": 5.6902,
        "radius_meters": 500,
        "image": SAMPLES_DIR / "found_black_wallet.png",
    },
    "found_brown": {
        "label": "Found brown wallet",
        "report_type": "found",
        "description": (
            "Brown bifold wallet with cash only, no cards. Found at the train station."
        ),
        "latitude": 50.8490,
        "longitude": 5.7050,
        "radius_meters": 500,
        "image": SAMPLES_DIR / "found_brown_wallet.png",
    },
    "found_phone": {
        "label": "Found phone (mismatch)",
        "report_type": "found",
        "description": (
            "Blue smartphone with a cracked protective case left on a café table."
        ),
        "latitude": 52.3702,
        "longitude": 4.8952,
        "radius_meters": 500,
        "image": SAMPLES_DIR / "found_blue_phone.png",
    },
    "lost_keys": {
        "label": "Lost keys",
        "report_type": "lost",
        "description": (
            "Set of three silver house keys on a blue plastic key fob. "
            "Lost outside the student cafeteria."
        ),
        "latitude": 50.8514,
        "longitude": 5.6900,
        "radius_meters": 500,
        "image": SAMPLES_DIR / "lost_silver_keys.png",
    },
    "found_keys": {
        "label": "Found keys",
        "report_type": "found",
        "description": (
            "Metal keys with a blue tag found on a bench near the cafeteria."
        ),
        "latitude": 50.8515,
        "longitude": 5.6901,
        "radius_meters": 500,
        "image": SAMPLES_DIR / "found_silver_keys.png",
    },
}
