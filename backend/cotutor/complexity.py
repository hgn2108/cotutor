"""Compare a claimed Big-O against the growth rate measured by the harness."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Verdict = Literal["consistent", "slower_than_claimed", "faster_than_claimed", "inconclusive"]

# Expected log-log slope for common single-variable classes. n log n measures a bit above 1.
_CLASSES: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"^o\((1|logn|log\(n\))\)$"), 0.0),
    (re.compile(r"^o\((sqrt\(n\)|n\^0\.5|√n)\)$"), 0.5),
    (re.compile(r"^o\(n\)$"), 1.0),
    (re.compile(r"^o\(n\*?log\(?n\)?\)$"), 1.1),
    (re.compile(r"^o\(n(\^2|²|\*n)\)$"), 2.0),
    (re.compile(r"^o\(n(\^2|²)\*?log\(?n\)?\)$"), 2.1),
    (re.compile(r"^o\(n(\^3|³)\)$"), 3.0),
]


EXPONENTIAL = 99.0  # stands in for "grows faster than any polynomial"
_EXPONENTIAL = re.compile(r"(\d|[a-z)])\^\(?[a-z]|[a-z]!|\bfactorial|exponential|[²³]?ⁿ")


def _first_big_o(claim: str) -> str:
    """'O(1) per get and put' -> 'O(1)'."""
    m = re.search(r"O\((?:[^()]|\([^()]*\))*\)", claim)
    return m.group(0) if m else claim


def normalize_claim(claim: str) -> str:
    return re.sub(r"[\s*·×]", "", claim.lower())


def expected_slope(claim: str) -> float | None:
    """Log-log slope a claimed Big-O implies on doubling n; EXPONENTIAL for 2^n, k^n, n!."""
    norm = re.sub(r"\s+", "", claim.lower()).replace("·", "*")
    if _EXPONENTIAL.search(norm):
        return EXPONENTIAL
    for pattern, slope in _CLASSES:
        if pattern.match(norm):
            return slope
    return None


@dataclass
class ComplexityCheck:
    claimed: str
    measured_slope: float | None
    expected_slope: float | None
    verdict: Verdict
    note: str


def check(claimed: str, measured: float | None, tolerance: float = 0.4,
          per_operation: bool = False) -> ComplexityCheck:
    """``per_operation``: the claim is per call (design problems) while timing covers n calls,
    so the total grows one power of n faster than the claim."""
    exp = expected_slope(_first_big_o(claimed) if per_operation else claimed)
    if per_operation and exp is not None and exp != EXPONENTIAL:
        exp += 1.0
    if measured is None:
        return ComplexityCheck(claimed, None, exp, "inconclusive",
                               "Runs were too fast to time reliably.")
    if exp == EXPONENTIAL:
        return ComplexityCheck(claimed, measured, None, "inconclusive",
                               f"Measured growth ≈ n^{measured:.2f}; exponential claims can't be "
                               "checked with a polynomial fit.")
    if exp is None:
        return ComplexityCheck(claimed, measured, None, "inconclusive",
                               f"Measured growth ≈ n^{measured:.2f}; claim is multi-variable "
                               "or unusual, so it was not auto-checked.")
    if abs(measured - exp) <= tolerance:
        verdict: Verdict = "consistent"
    else:
        verdict = "slower_than_claimed" if measured > exp else "faster_than_claimed"
    return ComplexityCheck(claimed, measured, exp, verdict,
                           f"Measured growth ≈ n^{measured:.2f} vs ≈ n^{exp:.1f} expected "
                           f"for {claimed}.")
