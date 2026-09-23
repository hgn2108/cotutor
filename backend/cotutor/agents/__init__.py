"""The specialist agents. Each is one focused LLM call with a narrow, typed contract.

Agents only *propose* (specs, tests, code, fixes, lessons); nothing they claim is trusted
until the pipeline has executed it. Prompts therefore ask for executable artifacts rather
than assertions: a brute-force oracle instead of hand-computed expected outputs, a checker
instead of "any order is fine", an input generator instead of "it's O(n)".
"""

from .analyst import analyze
from .coach import coach_deep, coach_intro
from .debugger import debug
from .solver import solve
from .test_designer import design_tests
from .tutor import explain

__all__ = ["analyze", "coach_deep", "coach_intro", "debug", "design_tests", "explain", "solve"]
