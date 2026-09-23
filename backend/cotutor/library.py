"""The curated problem library shown on the home page (statements written for Cotutor)."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

LIBRARY_PATH = Path(__file__).parent / "data" / "problems.json"


@cache
def problems() -> list[dict[str, Any]]:
    return json.loads(LIBRARY_PATH.read_text())
