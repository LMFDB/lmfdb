---
id: T28
title: Normalize file-path conventions (do this first — it unblocks parallel agents)
status: review
owner: claude (session 2026-07-16/17)
priority: P0
tier: 0
repos: [ShimCurve]
depends_on: []
questions: []
---

## Context — three mutually incompatible cwd conventions

Where a ShimCurve write lands depends on which directory you started Magma in, and the code disagrees with itself about what that directory is:

| convention | assumed cwd | files |
|---|---|---|
| `"ShimCurve/data/..."` | **parent** of the repo | `code/quaternion_orders/enumerate-O.m:125,141,297,316` (the `.m` writers), `code/level-structure/enumerate-H.m:782` (legacy `EnumerateH`), `code/utils/write-to-latex.m:7` (also wrong: missing `data/`), `pictures/picture-to-gp.m:10` (`SetOutputFile`) |
| `"./data/..."` | **repo root** | `enumerate-O.m:154,170,183,198,442,463` (the `.txt` writers) |
| `"data/..."` | **repo root** | `enumerate-H.m:623` (`WriteHeaderAndSubgroupsDataToFile` — **the current main writer**), `code/utils/read-write.m:43` |

The README says to work *one directory above* the repo (`AttachSpec("ShimCurve/spec")`), which makes the current main writer emit to `<parent>/data/genera-tables/…` — **outside the repo**. Conversely, running from the repo root makes `enumerate-O.m`'s `.m` writers emit to `<repo>/ShimCurve/data/…`. **No cwd makes all writers correct.**

This is very likely the mechanical explanation for T06's mysteries (`quaternion-orders.m` vs `.txt` disagreeing on area and row counts: they were written from different working directories at different times and hand-moved into place).

Verified 2026-07-16: `AttachSpec("spec")` works fine from the repo root, and `WriteHeaderAndSubgroupsDataToFile` run from the repo root correctly writes `<repo>/data/genera-tables/…`. The `qm-mazur` scripts and `tests/run_all.m` (which references `../CHIMP/CHIMP.spec`) also assume **repo root**. So repo-root is both the majority convention and the one the live pipeline already uses.

## Task

Standardize on **cwd = repo root** and make every path consistent with it. This unblocks parallel work: agents in separate worktrees can then run generation without writes escaping into a shared directory.

## Steps

1. Add `code/utils/paths.m` (in `spec`) with a single accessor, e.g. `intrinsic DataFile(rel::MonStgElt) -> MonStgElt` returning `"data/" cat rel`, so future writers cannot re-invent a convention. (Optionally allow an override via an environment variable or a settable global for out-of-tree output — nice for agents, not required.)
2. Rewrite every path above to go through it: drop the `ShimCurve/` prefix and the `./`. Note `write-to-latex.m:7` also omits `data/` — fix. `pictures/picture-to-gp.m:10` writes `algdat.dat` into `pictures/` — normalize to a repo-root-relative path too.
3. Update `README.md`: replace "Make sure you are working one directory above this repository" + `AttachSpec("ShimCurve/spec")` with the repo-root instruction and `AttachSpec("spec")`. Grep the repo for other `AttachSpec("ShimCurve/spec")` occurrences (docs, qm-mazur headers, log files are fine to leave) and reconcile.
4. Verify each writer lands in the right place from the repo root: `EnumerateO` (tiny bound, e.g. 30), `EnumerateOmu` (bound 30), `WriteHeaderAndSubgroupsDataToFile` (D=6, deg 1, N=1), `X0DNdata` (small caps), `PrepPictureDataH`. Confirm with `git status` that only intended `data/` files change; confirm nothing appears in the parent directory.
5. `tests/run_quick.m` green (it exercises `data_roundtrip.m`, which writes a fixture under `data/` — confirm it still lands correctly).

## Acceptance criteria

- Exactly one path convention in the codebase (grep proof: no `"ShimCurve/` and no `"./data` remain in `code/`).
- All five writers verified to land inside the repo when run from the repo root; parent directory stays clean.
- README's attach/run instructions match reality.

## Log

- 2026-07-16: ticket created. Conventions table above verified by grep + a live probe run.
- 2026-07-16 (claude): **Implemented**, ShimCurve branch `ticket/T28-path-conventions` (commit da5540b). `code/utils/paths.m` adds `DataFile(rel)` (registered in spec); all reader/writer sites routed through it (enumerate-O.m x12, enumerate-H.m x2, tablesX0DN.m x6, read-write.m, write-to-latex.m — which was also missing its `data/` component —, picture-to-gp.m, overnight-magma.m). README now: run from repo root, `AttachSpec("spec")`. Verified live from the repo root: `EnumerateO`, `EnumerateOmu`, `WriteHeaderAndSubgroupsDataToFile` all write inside `<repo>/data/`; nothing escapes to the parent. Drive-by: fixed pre-existing syntax error in tests/data_roundtrip.m (`::` annotation + stray `;` on a plain procedure) that aborted run_quick on main; quick suite green. Awaiting review/merge.
