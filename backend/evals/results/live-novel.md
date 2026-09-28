## Evaluation: live-novel

Original problems given as pasted statements · models gemini-3.8-flash with fallbacks

Runs scored: 16

| Metric | Result |
|---|---|
| **Correct** (hidden golden tests) | 15/16 (94%) |
| Verified by the pipeline | 16/16 (100%) |
| **Verified → actually correct** (precision) | 15/16 (94%) |
| First draft correct (before debugging) | 16/16 (100%) |
| Rescued by the debugger | 0 |
| Bugs caught only by random stress testing | 1 |
| Brute-force oracle trusted | 14/16 (88%) |
| Claimed Big-O matches ground truth | 12/13 (92%) · 3 not auto-scorable |
| Coach names the right pattern | 15/16 (94%) |
| Complete lessons | 16/16 (100%) |
| Median LLM calls · tokens | 7 · 10,413 |
| Latency median · p90 | 17 s · 24 s |
| Runs that fell back to a lighter model | 2/16 (12%) |

Naive-brute-force check outcomes: inconclusive 1, naive 5, optimal 4, rewritten 3, skipped 3.

**False verifications:**
- novel-rate-limiter

**Incorrect final solutions:**
- novel-rate-limiter: fail on [['RateLimiter', 'allow', 'allow', 'allow'], [[1, 1], [5], [: expected [None, True, False, True] got [None, True, True, True]

**Caught by stress testing:**
- novel-split-equal-blocks

**Pattern misses:**
- novel-split-equal-blocks: Backtracking
