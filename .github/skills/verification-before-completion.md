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
| Tests pass | `uv run python -m pytest -q -m "not integration"` | `N passed`, 0 failed (~370 tests) |
| Coverage held | same command — coverage prints via `--cov-report=term-missing` | `src/` total stays ~95%; new code not in the Missing column (no enforced gate yet — CI gate planned) |
| Regression suite green | `uv run python -m pytest tests/regression/ -q` | All clip + classify tests pass |
| CLI works | `./md.sh analyze <video> --lift snatch` (or `lifts` / `phases` / `rules` for KB claims) | Expected output, exit code 0 |
| KB rule added | `uv run python main.py rules <lift> <phase>` | New rule listed with bands, feedback, priority |
| Annotated output correct | Open the output MP4 / regenerated clip under `tests/regression/clips/` | Overlay visually matches the claim |
| AC verified | Read AC, check each Given/When/Then | Each criterion explicitly confirmed |

Lint / type-check / security-scan claims: those tools are **planned — not yet configured** in this repo. There is nothing to run, so never claim "lint clean" or "mypy passes" here.

## Common Failures

| Claim | What is required | What is NOT sufficient |
|---|---|---|
| "Tests pass" | pytest output showing 0 failures | "Should pass", previous run, inference |
| "Coverage held" | The printed coverage table from this run | "I added tests for everything" |
| "AC met" | Step through each Given/When/Then | "The tests cover it" |
| "Bug fixed" | Reproduce original symptom, confirm it no longer occurs | Code changed |
| "Fixture works" | Regression test run discovering and passing the new fixture | "The YAML looks right" |
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
| "The unit tests passed" | Unit tests ≠ regression suite ≠ real CLI run |
| "Agent reported success" | Verify independently |
| "Partial check is enough" | Partial proves nothing |
