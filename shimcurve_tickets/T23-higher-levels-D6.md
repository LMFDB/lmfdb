---
id: T23
title: Higher levels for D = 6 (including the missing N = 5)
status: open
owner: none
priority: P2
tier: 3
repos: [ShimCurve]
depends_on: [T10]
questions: [Q12]
---

## Context

D=6 data stops at N ∈ {1,2,3,4,6}: N=5 is blocked by the index-2 assertion (T10), and nothing above 6 has been attempted. Q12.1 sets the target (suggest N ≤ 12 or a prime/prime-power set — note D=6 excludes N divisible by 2 or 3 only where coprimality is required; N=4 and 6 shipped, so non-coprime N are evidently in scope for the enhanced construction — confirm which N are mathematically admissible before running: the machinery asserts N > 2 internally and uses the ×3 lifting trick for N ≤ 2, `enumerate-H.m:324-330`).

Cost realism: subgroup counts grow fast (N=6 deg-6 already 475 rows / 33 min). `Subgroups(G, KG)` for N=8,9,12 may be substantially heavier — measure before committing to a range. Timings inform Q12.

## Steps

1. After T10 lands: generate N=5 (all three degrees), run the T10 sanity battery, stage.
2. Probe N ∈ {7, 8, 9, 12} for deg 1 with a timing cap (background run, note `#G`, `#Subgroups(G,KG)`, wall time). Report the cost curve in the Log → feeds the Q12 scope decision.
3. Generate the Q12-approved range across all degrees; validate (coarse genus vs `SignatureX0DN(6,N)` where applicable, label uniqueness, area asserts).
4. Watch for new failure modes at composite N (the prime_kernels filtering logic, `enumerate-H.m:347-350`, has only ever seen N with radical {2,3}; N=10, 12 exercise it differently). Any assertion trip = Log entry + investigation, not a bypass.
5. Stage files + commands.

## Acceptance criteria

- N=5 shipped-quality files exist and cross-check; cost table for N ≤ 12 in the Log; approved range generated and validated.

## Log

- 2026-07-16: ticket created from survey.
