# Sample test data

Use these descriptions and images in **Report Item**, then open **Matches**.

Images live in `samples/images/`. Copy-paste the description text into the form and upload the matching PNG.

Default map pin in the app (Maastricht) works for all “nearby” examples. For a far mismatch, change latitude to `52.3702` (Amsterdam).

---

## Scenario A — strong wallet match

| Role | Description (copy) | Image |
|------|--------------------|-------|
| **Lost** | Small black leather wallet with a blue bank card and student ID inside. Lost near the university library. | `lost_black_wallet.png` |
| **Found** | Black wallet found by the university library entrance. Contains cards and looks like leather. | `found_black_wallet.png` |

Use the same date/time (±1 hour) and keep the default location/radius.

**Expect:** high text + geo + time; image score should also be high if CLIP is loaded.

---

## Scenario B — wallet distractor (weaker)

| Role | Description (copy) | Image |
|------|--------------------|-------|
| **Lost** | *(same as Scenario A lost)* | `lost_black_wallet.png` |
| **Found** | Brown bifold wallet with cash only, no cards. Found at the train station. | `found_brown_wallet.png` |

Same place/time as A, or move the found report ~2 km away.

**Expect:** lower text/image than Scenario A; overall rank should put A above B.

---

## Scenario C — keys match

| Role | Description (copy) | Image |
|------|--------------------|-------|
| **Lost** | Set of three silver house keys on a blue plastic key fob. Lost outside the student cafeteria. | `lost_silver_keys.png` |
| **Found** | Metal keys with a blue tag found on a bench near the cafeteria. | `found_silver_keys.png` |

**Expect:** strong keys ↔ keys match; should not top-rank against the wallet lost item.

---

## Scenario D — clear mismatch

| Role | Description (copy) | Image |
|------|--------------------|-------|
| **Lost** | *(wallet from A)* | `lost_black_wallet.png` |
| **Found** | Blue smartphone with a cracked protective case left on a café table. | `found_blue_phone.png` |

Optionally set found time to 3 days later and latitude `52.3702`.

**Expect:** low overall score vs Scenario A.

---

## Scenario E — backpack / bag

| Role | Description (copy) | Image |
|------|--------------------|-------|
| **Lost** | Red backpack with a laptop sleeve and a water bottle pocket. Lost at the main bus stop. | `lost_red_backpack.png` |
| **Found** | Red bag found at the bus stop, looks like a student backpack. | `found_red_bag.png` |

---

## Quick demo script

1. Submit **Lost** from Scenario A (description + `lost_black_wallet.png`).
2. Submit **Found** from A, B, C, and D (each with its image).
3. Open **Matches**, select the lost wallet.
4. Check ranking: A first, B mid, phone last; keys should not beat the dark wallet.

For offline/CI without model downloads:

```bash
LOST_FOUND_MOCK_ML=1 streamlit run app.py
```
