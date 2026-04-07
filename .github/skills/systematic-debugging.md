---
name: systematic-debugging
description: Root-cause-first debugging protocol for the engineer. Prevents guess-and-check thrashing. Mandatory before proposing any fix.
---

# Systematic Debugging

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you have not completed Phase 1, you cannot propose fixes. A symptom fix is a failure mode.

## When to Use

Use for **any** technical issue:
- Test failures
- Unexpected behavior or data
- Build failures
- Integration issues
- Performance problems

Use this **especially** when:
- "The fix seems obvious" — obvious fixes are where assumptions hide
- You have already tried one fix that didn't work
- You don't fully understand why the failure is happening
- The failure is intermittent

## The Four Phases

Complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

**Before attempting any fix:**

1. **Read the error completely** — stack trace, line numbers, file paths. The error message usually contains the answer. Don't skim it.

2. **Reproduce consistently** — can you trigger the failure reliably? If not, gather more data. Don't guess at a cause you can't reproduce.

3. **Check what changed** — `git diff`, `git log --oneline -10`. What was the last change before this broke?

4. **For multi-component failures** — add diagnostic instrumentation at each boundary before proposing fixes:
   ```python
   # Example: ingestion pipeline failure
   logger.debug("yfinance response: %s", df.shape)          # what entered normalization?
   logger.debug("normalized rows: %d", len(price_rows))     # what exited normalization?
   logger.debug("storage upsert result: %s", result)        # what hit the DB?
   ```
   Run once to see where it breaks, then investigate that component.

5. **Trace data flow** — where does the bad value originate? Trace backward through the call stack to the source. Fix at the source, not at the symptom.

### Phase 2: Pattern Analysis

1. Find working similar code in the codebase — what does the passing equivalent look like?
2. Compare the working and broken cases — list every difference, however small
3. Understand dependencies — what config, env vars, or external state does the broken component assume?

### Phase 3: Hypothesis and Testing

1. **Form one hypothesis**: "I think X is the root cause because Y" — write it down before acting
2. **Make the smallest possible change** to test that hypothesis — one variable at a time
3. **Verify the result** — did it fix the issue? If no, form a new hypothesis. Do not stack multiple changes.

### Phase 4: Implementation

1. **Write a failing test** that reproduces the root cause (see `test-driven-development` skill)
2. **Implement one fix** targeting the root cause
3. **Verify** the test passes, no other tests broke

**If 3+ fixes have failed**: stop. This is an architectural problem, not a bug. Raise it with the architect before continuing.

## Red Flags — Stop and Return to Phase 1

You are doing it wrong if you think:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "I'll add multiple changes and run tests"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "One more fix attempt" (when 2 have already failed)

All of these mean: **stop, return to Phase 1**.

## Common Rationalizations to Reject

| Excuse | Reality |
|---|---|
| "The issue is simple, no need for process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "I see the problem, let me fix it" | Seeing the symptom ≠ understanding the root cause. |
| "Multiple changes at once saves time" | You can't isolate what worked. You will introduce new bugs. |
| "I'll write the test after confirming the fix works" | Untested fixes don't stick. Test first proves causation. |
| "3 failed fixes — one more attempt" | 3 failures = architectural problem. Raise it, don't iterate. |

## Phase Summary

| Phase | Key activity | Done when |
|---|---|---|
| 1. Root cause | Read error, reproduce, trace data flow | You understand *what* and *why* |
| 2. Pattern | Compare working vs. broken | Differences identified |
| 3. Hypothesis | Single theory, minimal test | Confirmed or disproved |
| 4. Implementation | Failing test, fix, verify | Tests pass, no regressions |

## Related Skills

- `test-driven-development` — writing the failing test in Phase 4
- `verification-before-completion` — verifying the fix actually worked before claiming success
