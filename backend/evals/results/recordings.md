## Evaluation: recordings

49 recorded lessons scored against independent golden solutions. Recordings are only saved when a run verifies, so the correct and verified rates are upper bounds (survivorship). What this measures is whether *verified* can be trusted, and teaching accuracy. Live runs (`--live`) measure unbiased success rates.

| Metric | Result |
|---|---|
| **Correct** (hidden golden tests) | 49/49 (100%) |
| Verified by the pipeline | 49/49 (100%) |
| **Verified → actually correct** (precision) | 49/49 (100%) |
| First draft correct (before debugging) | 49/49 (100%) |
| Rescued by the debugger | 0 |
| Bugs caught only by random stress testing | 0 |
| Brute-force oracle trusted | 45/49 (92%) |
| Claimed Big-O matches ground truth | 44/44 (100%) · 5 not auto-scorable |
| Coach names the right pattern | 48/49 (98%) |
| Complete lessons | 49/49 (100%) |
| Median LLM calls · tokens | 6 · 7,910 |
| Latency median · p90 | 17 s · 50 s |
| Runs that fell back to a lighter model | 12/49 (24%) |

Naive-brute-force check outcomes: inconclusive 6, naive 17, optimal 11, rewritten 7, skipped 8.

**Pattern misses:**
- top-k-frequent-elements: Hash map lookup
