"""Resolve a coarse item type from category labels and description keywords."""

from __future__ import annotations

import re

from models.schemas import Report

_CATEGORY_ALIASES = {
    "wallet": "wallet",
    "purse": "wallet",
    "bag": "bag",
    "keys": "keys",
    "phone": "phone",
    "laptop": "laptop",
    "jewelry": "jewelry",
    "id or documents": "documents",
    "clothing": "clothing",
    "bottle": "bottle",
    "glasses": "glasses",
    "earbuds": "earbuds",
    "electronics": "earbuds",
}

# More specific phrases first so "card holder" wins over generic words.
_TYPE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("wallet", re.compile(r"\b(card[\s-]?holder|billfold|bifold|purse|wallet)\b")),
    ("bag", re.compile(r"\b(backpack|rucksack|suitcase|handbag|duffel|tote)\b")),
    ("bag", re.compile(r"\bbags?\b")),
    ("keys", re.compile(r"\bkeys?\b")),
    ("phone", re.compile(r"\b(smartphone|iphone|android|phone)\b")),
    ("laptop", re.compile(r"\b(laptop|macbook|notebook computer)\b")),
    ("bottle", re.compile(r"\bbottle\b")),
    ("glasses", re.compile(r"\b(glasses|spectacles|eyeglasses)\b")),
    ("earbuds", re.compile(r"\b(airpods?|earbuds?|earphones?)\b")),
)


def infer_item_type(text: str) -> str | None:
    lowered = text.lower()
    for item_type, pattern in _TYPE_PATTERNS:
        if pattern.search(lowered):
            return item_type
    return None


def resolved_item_type(report: Report) -> str | None:
    category = (report.category or "").strip().lower()
    if category and "mock" not in category and category != "unclassified":
        aliased = _CATEGORY_ALIASES.get(category)
        if aliased:
            return aliased
        if category != "other":
            return category
    return infer_item_type(report.description)
