# Sample test data

The photos in `samples/images/` back both the demo seed (`services/demo_seed.py`) and the
"Try a sample" presets in the report form (`samples/presets.py`, served by
`GET /api/demo/presets`). Each item has two different photos: one for the lost report and
one for the found report, so the photo matcher has something real to compare.

The files were exported with dark letterbox bars; `python scripts/crop_samples.py` strips
them in place (already applied to the committed PNGs). `samples/mouse/` is unused.

Default map pins are in Maastricht. The "far" distractors use Amsterdam (`52.3702, 4.8952`).

---

## Seeded pairs

| Item | Lost (owner, photo) | Found (finder, photo) | Notes |
|------|---------------------|-----------------------|-------|
| Wallet | Alex, `lost_black_wallet.png` | Sam (anonymous), `found_black_wallet.png` | Mia's `found_brown_wallet.png` card holder at a hotel is a same-category distractor |
| AirPods | Alex, `lost_white_earbuds.png` | Mia, `found_white_earbuds.png` | Same bus stop, one hour apart |
| Keys | Sam, `lost_silver_keys.png` | Alex, `found_silver_keys.png` | Tapijn cafeteria |
| Glasses | Mia, `lost_black_glasses.png` | Sam (anonymous), `found_black_glasses.png` | Inner City Library |
| Bottle | Sam, `lost_green_bottle.png` | Mia, `found_green_bottle.png` | Noor's `found_green_bottle_far.png` is in Amsterdam, two days later |
| Backpack | Noor, `lost_red_backpack.png` | Alex, `found_red_bag.png` | Boschstraat bus stop |
| Phone | – | Sam, `found_blue_phone.png` | Amsterdam mismatch; should never rank against the wallet |

Event times run from three days ago to one hour ago so time scores differ per pair.

---

## Manual scenarios

Copy a description into **Report**, pick the matching sample photo, then open **Matches**.

### A — strong wallet match

| Role | Description | Image |
|------|-------------|-------|
| Lost | Small black leather wallet with a blue bank card and student ID inside. Lost near the university library. | `lost_black_wallet.png` |
| Found | Black wallet found by the university library entrance. Contains cards and looks like leather. | `found_black_wallet.png` |

Expect: high text, place, and time scores; photo score high when the vision stack is loaded.

### B — wallet distractor

| Role | Description | Image |
|------|-------------|-------|
| Found | Brown bifold wallet with cash only, no cards. Found at the train station. | `found_brown_wallet.png` |

Expect: same category as A but lower text and photo scores, so A ranks above B.

### C — keys

| Role | Description | Image |
|------|-------------|-------|
| Lost | Set of three silver house keys on a blue plastic key fob. Lost outside the student cafeteria. | `lost_silver_keys.png` |
| Found | Metal keys with a blue tag found on a bench near the cafeteria. | `found_silver_keys.png` |

### D — clear mismatch

| Role | Description | Image |
|------|-------------|-------|
| Found | Blue smartphone with a cracked protective case left on a café table. | `found_blue_phone.png` |

Expect: hard category gate against the wallet, overall score 0.

### E — backpack

| Role | Description | Image |
|------|-------------|-------|
| Lost | Red backpack with a laptop sleeve and a water bottle pocket. Lost at the main bus stop. | `lost_red_backpack.png` |
| Found | Red bag found at the bus stop, looks like a student backpack. | `found_red_bag.png` |

### F — green bottle plus far distractor

| Role | Description | Image |
|------|-------------|-------|
| Lost | Dark green metal water bottle covered in environmental stickers. Lost by the Vrijthof bicycle racks. | `lost_green_bottle.png` |
| Found | Green reusable metal bottle covered with travel stickers, found beside the Vrijthof bike parking. | `found_green_bottle.png` |
| Found (far) | Plain dark green insulated bottle with a black cap, found on a path in Amsterdam. | `found_green_bottle_far.png` |

### G — glasses

| Role | Description | Image |
|------|-------------|-------|
| Lost | Black rectangular prescription glasses with a blue hard case, lost in a university library study room. | `lost_black_glasses.png` |
| Found | Black rectangular glasses and a dark blue case found under a desk in the university library. | `found_black_glasses.png` |

### H — earbuds case

| Role | Description | Image |
|------|-------------|-------|
| Lost | Heavily scratched white wireless-earbuds charging case, lost near the main bus stop. | `lost_white_earbuds.png` |
| Found | Dirty white wireless-earbuds charging case found beside the bus-stop footpath. | `found_white_earbuds.png` |

---

## Photo sources

Externally hosted user or listing photos used for demo purposes only; redistribution
rights have not been verified.

- `lost_green_bottle.png`: CustomStickers.com blog photo
- `found_green_bottle.png`: Mercado Libre listing photo
- `found_green_bottle_far.png`: Poshmark listing photo
- `lost_black_glasses.png`: Pikabu user photo
- `found_black_glasses.png`: Letgo listing photo
- `lost_white_earbuds.png`: Allegro Lokalnie listing photo
- `found_white_earbuds.png`: Trojmiasto reader-submitted lost-and-found photo

---

## Resetting the demo

```bash
python -m scripts.seed_demo_db          # wipe data/lost_found.sqlite and data/uploads, reseed
```

Or use "Reload demo" on the Account page when the API runs with `LOST_FOUND_ALLOW_DEMO_RESET=1`.
For offline runs without model downloads start the API with `LOST_FOUND_MOCK_ML=1`.
