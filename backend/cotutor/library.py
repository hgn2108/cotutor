"""The curated problem library shown on the home page (statements written for Cotutor)."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data"
LIBRARY_PATH = DATA / "problems.json"
ROADMAPS_PATH = DATA / "roadmaps.json"


@cache
def problems() -> list[dict[str, Any]]:
    """The curated library shown on the home page (statements written for Cotutor)."""
    return json.loads(LIBRARY_PATH.read_text())


@cache
def roadmaps() -> dict[str, Any]:
    """Blind 75 / NeetCode 150: titles, numbers, patterns and signatures only (no statements)."""
    return json.loads(ROADMAPS_PATH.read_text())


def roadmap_problem(problem_id: str) -> dict[str, Any] | None:
    return next((p for p in roadmaps()["problems"] if p["id"] == problem_id), None)


def library_match(title: str) -> dict[str, Any] | None:
    """A library problem with the same title, whose recorded lesson can be reused."""
    return next((p for p in problems() if p["title"].lower() == title.lower()), None)


def name_prompt(item: dict[str, Any]) -> str:
    """Canonical input for a roadmap lesson: the problem's name and signature, never its text."""
    if "entry" in item:
        sig = f"Function signature: {item['entry']}({', '.join(item['params'])})"
    else:
        sig = f"Class: {item['class_name']}"
    return f"LeetCode {item['number']}: {item['title']}\n{sig}"


def lesson_input(item: dict[str, Any]) -> str:
    """What the pipeline runs for a roadmap problem: a library statement if one exists (so its
    recorded lesson is reused), otherwise the name and signature."""
    lib = library_match(item["title"])
    return lib["statement"] if lib else name_prompt(item)
