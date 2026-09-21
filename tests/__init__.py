"""Tests default to mock ML so CI never downloads Hugging Face weights."""

import os

os.environ.setdefault("LOST_FOUND_MOCK_ML", "1")
