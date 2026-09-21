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
    "lost_backpack": {
        "label": "Lost red backpack",
        "report_type": "lost",
        "description": (
            "Used red student backpack with a laptop sleeve and a mesh water-bottle "
            "pocket. Lost beside the main bus stop."
        ),
        "latitude": 50.8506,
        "longitude": 5.6907,
        "radius_meters": 350,
        "image": SAMPLES_DIR / "lost_red_backpack.png",
    },
    "found_backpack": {
        "label": "Found red backpack",
        "report_type": "found",
        "description": (
            "Worn red student backpack with black zips found on a bus-stop bench."
        ),
        "latitude": 50.8507,
        "longitude": 5.6908,
        "radius_meters": 350,
        "image": SAMPLES_DIR / "found_red_bag.png",
    },
    "lost_bottle": {
        "label": "Lost green bottle",
        "report_type": "lost",
        "description": (
            "Dark green metal water bottle covered in environmental stickers. "
            "Lost by the Vrijthof bicycle racks."
        ),
        "latitude": 50.8490,
        "longitude": 5.6879,
        "radius_meters": 250,
        "image": SAMPLES_DIR / "lost_green_bottle.png",
    },
    "found_bottle": {
        "label": "Found green bottle (match)",
        "report_type": "found",
        "description": (
            "Green reusable metal bottle covered with travel stickers, found beside "
            "the Vrijthof bike parking."
        ),
        "latitude": 50.8491,
        "longitude": 5.6881,
        "radius_meters": 250,
        "image": SAMPLES_DIR / "found_green_bottle.png",
    },
    "found_bottle_far": {
        "label": "Found green bottle (far distractor)",
        "report_type": "found",
        "description": (
            "Plain dark green insulated bottle with a black cap, found on a path "
            "in Amsterdam."
        ),
        "latitude": 52.3702,
        "longitude": 4.8952,
        "radius_meters": 300,
        "image": SAMPLES_DIR / "found_green_bottle_far.png",
    },
    "lost_glasses": {
        "label": "Lost black glasses",
        "report_type": "lost",
        "description": (
            "Black rectangular prescription glasses with a blue hard case, lost in "
            "a university library study room."
        ),
        "latitude": 50.8479,
        "longitude": 5.6884,
        "radius_meters": 200,
        "image": SAMPLES_DIR / "lost_black_glasses.png",
    },
    "found_glasses": {
        "label": "Found black glasses",
        "report_type": "found",
        "description": (
            "Black rectangular glasses and a dark blue case found under a desk in "
            "the university library."
        ),
        "latitude": 50.8480,
        "longitude": 5.6885,
        "radius_meters": 200,
        "image": SAMPLES_DIR / "found_black_glasses.png",
    },
    "lost_earbuds": {
        "label": "Lost white earbuds case",
        "report_type": "lost",
        "description": (
            "Heavily scratched white wireless-earbuds charging case, lost near the "
            "main bus stop."
        ),
        "latitude": 50.8506,
        "longitude": 5.6907,
        "radius_meters": 200,
        "image": SAMPLES_DIR / "lost_white_earbuds.png",
    },
    "found_earbuds": {
        "label": "Found white earbuds case",
        "report_type": "found",
        "description": (
            "Dirty white wireless-earbuds charging case found beside the bus-stop "
            "footpath."
        ),
        "latitude": 50.8507,
        "longitude": 5.6908,
        "radius_meters": 200,
        "image": SAMPLES_DIR / "found_white_earbuds.png",
    },
}
