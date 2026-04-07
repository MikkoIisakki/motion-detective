---
name: verification-before-completion
description: Evidence-first protocol before claiming any task is done, tests pass, or a fix worked. Used by engineer before self-review sign-off and by product-manager before AC validation.
---

# Verification Before Completion

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you have not run the verification command in this message, you cannot claim it passes.

## The Gate

Before claiming any status — done, passing, fixed, complete:

1. **Identify** — what command proves this claim?
2. **Run** — execute the full command fresh, in full
3. **Read** — read the full output, check exit code, count failures
4. **Verify** — does the output confirm the claim?
   - If **no**: state the actual status with evidence
   - If **yes**: state the claim **with** the evidence
5. **Only then**: make the claim

Skipping any step is asserting without evidence.

## Verification Commands for This Project

| Claim | Command | Success criteria |
|---|---|---|
| Tests pass | `pytest -q` | `N passed, 0 failed` |
| Coverage met | `pytest --cov=app --cov-report=term-missing` | No module below 80% |
| Lint clean | `ruff check backend/` | `All checks passed` |
| Type-safe | `mypy backend/app` | `Success: no issues found` |
| Security clean | `bandit -r backend/app -ll` | No HIGH or CRITICAL findings |
| Complexity within limit | `radon cc backend/app -n C` | No output (no CC > 10) |
| Migration applies cleanly | `psql ... -f db/migrations/NNN.sql` | No errors |
| Endpoint works | `curl -s http://localhost:8000/v1/...` | Expected JSON, expected status code |
| AC verified | Read AC, check each Given/When/Then | Each criterion explicitly confirmed |

## Common Failures

| Claim | What is required | What is NOT sufficient |
|---|---|---|
| "Tests pass" | `pytest` output showing 0 failures | "Should pass", previous run, inference |
| "Lint clean" | `ruff check` output showing 0 errors | "I didn't add any new code" |
| "AC met" | Step through each Given/When/Then | "The tests cover it" |
| "Bug fixed" | Reproduce original symptom, confirm it no longer occurs | Code changed |
| "Migration works" | Applied to a clean DB in CI | "SQL looks correct" |
| "Task done" | Self-review checklist fully checked | "Implementation is in place" |

## Red Flags — Stop

You are about to make an unverified claim if you use:
- "should", "probably", "seems to", "looks like"
- "I'm confident that", "this should work"
- "Done!", "Complete!", "All good!" — without having run the command
- Expressing satisfaction before verification
- Trusting a prior run from earlier in the session

## For the Engineer — Before Self-Review Sign-Off

Do not mark any item on the self-review checklist as complete unless you have run the corresponding command **in this session** and read the output. "Ran it earlier" does not count.

The checklist is not a declaration of intent. It is a record of evidence.

## For the Product-Manager — Before Accepting a Task

Do not accept a story based on "the tests cover it" or "the code is in place." Read each Given/When/Then criterion and confirm — by observation or test output — that the system actually behaves as described.

If any criterion cannot be verified by running a command or observing actual behavior, it is not verified.

## Rationalizations to Reject

| Excuse | Reality |
|---|---|
| "Should work now" | Run the command |
| "I'm confident" | Confidence is not evidence |
| "I checked it earlier" | Fresh verification, in this message |
| "The linter passed" | Linter ≠ type checker ≠ tests ≠ runtime |
| "Agent reported success" | Verify independently |
| "Partial check is enough" | Partial proves nothing |
