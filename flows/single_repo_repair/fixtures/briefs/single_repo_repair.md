Fix the seeded pagination bug in `tiny_issue_service`.

Page 1 currently skips the first issue instead of returning the first window.
Keep the repair narrow, prove it with deterministic local pytest output, and
route the finished work through review before the run closes.
