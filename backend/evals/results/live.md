## Evaluation: live

Fresh runs from problem names · models gemini-3.8-flash with fallbacks

Runs scored: 55

| Metric | Result |
|---|---|
| **Correct** (hidden golden tests) | 55/55 (100%) |
| Verified by the pipeline | 53/55 (96%) |
| **Verified → actually correct** (precision) | 53/53 (100%) |
| First draft correct (before debugging) | 54/55 (98%) |
| Rescued by the debugger | 1 |
| Bugs caught only by random stress testing | 0 |
| Brute-force oracle trusted | 48/55 (87%) |
| Claimed Big-O matches ground truth | 48/48 (100%) · 7 not auto-scorable |
| Coach names the right pattern | 50/55 (91%) |
| Complete lessons | 55/55 (100%) |
| Median LLM calls · tokens | 6 · 9,251 |
| Latency median · p90 | 19 s · 44 s |
| Runs that fell back to a lighter model | 15/55 (27%) |

Naive-brute-force check outcomes: inconclusive 11, naive 21, optimal 7, rewritten 7, skipped 9.

**Debugger rescues:**
- koko-eating-bananas

**Pattern misses:**
- merge-two-sorted-lists: Iterative Dummy Head
- reorder-list: In-place linked list manipulation
- number-of-islands: Breadth-First Search
- linked-list-cycle: Hash set
- serialize-and-deserialize-binary-tree: Depth-First Search
