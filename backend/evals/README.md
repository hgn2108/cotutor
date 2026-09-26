# Evaluation

The pipeline marks its own solutions as *verified*. An evaluation can't rely on that, so it
scores every run against **independent ground truth**.

## Golden set

[`golden.py`](golden.py) has 49 Blind 75 / NeetCode 150 problems. Each one includes:

- a hand-written, known-correct solution
- hidden test inputs chosen to break wrong solutions (empty inputs, duplicates, negatives, boundaries, ties)
- the optimal time complexity and the accepted pattern names

Expected outputs come from running the golden solution, never from the pipeline. The goldens are
tested themselves in CI ([`tests/test_evals.py`](../tests/test_evals.py)): each one must reproduce
known answers and run every hidden case.

## Metrics

| Metric | Why it matters |
|---|---|
| Correct | Final solution passes the hidden golden tests |
| Verified → actually correct (precision) | Whether learners can trust the "verified" badge. A false verification is the worst failure |
| First draft correct / debugger rescues | Value of the verify ⟲ debug loop |
| Caught only by stress testing | Bugs that examples and edge cases missed and random differential testing found |
| Oracle trusted | How often the generated brute force reproduces the problem's examples |
| Claimed Big-O matches truth | Correctness of what the lesson teaches about complexity |
| Pattern named correctly | Whether the pattern quiz's answer is right (keyword match; strict) |
| Complete lessons, cost, latency, fallbacks | Reliability and cost on the free tier |

## Running

```bash
uv run python -m evals.run                       # score recorded lessons (free; survivorship-biased)
uv run python -m evals.run --live                # fresh runs of all 49 problems from their names
uv run python -m evals.run --live --no-debug     # ablation: no debug loop
```

Results are written to [`results/`](results/) as JSON (per-run scores) and Markdown.

## Caveats

- Recorded lessons are saved only when a run verifies, so their success rates are upper bounds.
  Use live runs for unbiased rates.
- Free-tier model availability varies by the minute. Latency and which model answered depend on
  when the run happened, so each report states its models.
- Pattern grading is a strict keyword match. A rubric-based LLM judge for lesson quality
  (hint leakage, faithful restatement, derivation consistency) is the next step.
