"""Demo presets for quick form fill and match seeding."""

from pathlib import Path

from utils.config import PROJECT_ROOT

SAMPLES_DIR = PROJECT_ROOT / "samples" / "images"

PRESETS: dict[str, dict] = {
    "lost_wallet": {
        "label": "Lost wallet",
        "report_type": "lost",
        "description": (
            "Small black leather wallet. I had my UM student card and a blue "
            "ING debit card in it. Last saw it on a desk in Inner City Library."
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
            "Black leather wallet left on a table near the Inner City Library "
            "entrance. Cards still inside."
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
            "Brown bifold card holder a guest left on the hotel reception desk. "
            "Cash inside, no bank cards."
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
            "Blue smartphone in a cracked case, left on a café table in Amsterdam."
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
            "Three silver house keys on a blue plastic fob. I think they fell "
            "off my bag outside the Tapijn cafeteria."
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
            "Bunch of metal keys with a blue tag, sitting on a bench by the "
            "Tapijn cafeteria."
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
            "Old red student backpack with a laptop sleeve. I put it down at "
            "the Boschstraat bus stop and it was gone when the bus came."
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
            "Worn red backpack with black zips, left on a bench at the bus stop "
            "near campus."
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
            "Dark green metal bottle covered in festival stickers. Last had it "
            "locked to my bike at the Vrijthof racks."
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
            "Green reusable metal bottle with travel stickers, next to the "
            "Vrijthof bike parking."
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
            "Plain dark green insulated bottle with a black cap, on a path in "
            "Vondelpark in Amsterdam."
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
            "Black rectangular glasses in a blue hard case. I took them off in "
            "a study room at Inner City Library and left them under the desk."
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
            "Black rectangular glasses and a dark blue case under a desk in "
            "Inner City Library."
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
            "Scratched white wireless-earbuds case. Probably dropped it getting "
            "on the bus at Boschstraat."
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
            "Dirty white earbuds charging case on the footpath by the campus "
            "bus stop."
        ),
        "latitude": 50.8507,
        "longitude": 5.6908,
        "radius_meters": 200,
        "image": SAMPLES_DIR / "found_white_earbuds.png",
    },
}
