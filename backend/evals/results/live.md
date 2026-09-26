## Evaluation: live

49 fresh runs from problem names · models gemini-3.8-flash → fallbacks

| Metric | Result |
|---|---|
| **Correct** (hidden golden tests) | 4/4 (100%) |
| Verified by the pipeline | 4/4 (100%) |
| **Verified → actually correct** (precision) | 4/4 (100%) |
| First draft correct (before debugging) | 4/4 (100%) |
| Rescued by the debugger | 0 |
| Bugs caught only by random stress testing | 0 |
| Brute-force oracle trusted | 4/49 (8%) |
| Claimed Big-O matches ground truth | 4/4 (100%) · 0 not auto-scorable |
| Coach names the right pattern | 4/4 (100%) |
| Complete lessons | 4/49 (8%) |
| Median LLM calls · tokens | 1 · 784 |
| Latency median · p90 | 16 s · 21 s |
| Runs that fell back to a lighter model | 49/49 (100%) |

Naive-brute-force check outcomes: naive 3, rewritten 1.
