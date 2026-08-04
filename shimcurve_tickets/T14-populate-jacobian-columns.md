---
id: T14
title: Populate Jacobian columns for all rows
status: review
owner: wave2-K-opus
priority: P1
tier: 2
repos: [ShimCurve, lmfdb, db-readonly]
depends_on: [T13, T30]
questions: [Q13]
---

## Context

Fill, for all 2,587 rows (2,198 enhanced D=6 rows + 389 coarse rows; grows with Tier 3): `newforms, dims, mults, conductor, log_conductor, rank, simple, squarefree, genus_minus_rank, traces, trace_hash`. Currently populated only on the 339 coarse rows (plus `newforms` on 1,711). Genus-0 rows get the trivial values (empty arrays, rank 0 — copy modcurve's convention for genus 0: check `gps_gl2zhat_fine` genus-0 rows and mirror exactly).

These columns power the frontend's Jacobian section and the friends links (`web_curve.py:319-341` matches `newforms` and `trace_hash` against `lfunc_instances`).

## Steps

1. Magma pass (uses T13's `JacobianData`): iterate the regenerated data files (or a driver over the shipped (D, deg, N) parameters), compute per-H: `newforms, dims, mults, simple` (one newform, mult 1, dim = genus), `squarefree` (all mults = 1), `conductor` (per Q13.1 semantics — modcurve stores factored `[[p,e],...]`? verify with `select conductor from gps_gl2zhat_fine where genus>0 limit 3;` and copy), `traces` (a_p of Jac = Σ mults·(newform a_p sums over the orbit) — modcurve stores the first ~1000? check length convention), `genus_minus_rank` left for step 2. Write intermediate file keyed by label.
2. Python pass (`sage -python`, read-only db): for each row's newform list, pull `analytic_rank` (and `dim`) from `db.mf_newforms`; `rank = Σ mult·analytic_rank` (per Q13.1); `genus_minus_rank = genus − rank`; `log_conductor = Σ mult·log(newform conductor^dim)`? — **derive the formula from how modular curves computed it** (check `gps_gl2zhat_fine.log_conductor` vs conductor on 3 rows rather than guessing); `trace_hash` via `lmfdb.utils.trace_hash` (import `TraceHashClass`/the standard function — find it: `grep -r "trace_hash" ~/claude/lmfdb/lmfdb/utils/`) applied per modcurve convention (hash of the Jacobian's a_p sequence; confirm against one modcurve row by recomputation).
3. Missing-newform handling: if a needed CMF isn't in cmfdata/LMFDB range, leave the row's columns NULL and count it; report the count + the max level needed in the Log (drives cmfdata regeneration).
4. Cross-checks before staging: (a) recompute the 339 already-populated rows — must match exactly (any mismatch: investigate, do not overwrite silently, log it); (b) Σ dims·mults = genus for every row; (c) `simple ⟺ len(dims)==1 and mults==[1]`; (d) traces of the coarse curve X₀(6;N) match `JLDecomposition` output.
5. Stage `artifacts/T14-jacobian-update.txt` (`update_from_file` format, label-keyed) + load commands in the Log.
6. Post-load verification plan: friends links appear on a genus>0 curve page (e.g. the genus-1 curves should link to elliptic curves/CMFs via trace_hash match).

## Acceptance criteria

- All shipped rows either populated or NULL-with-reason (tallied in the Log).
- The four cross-checks pass corpus-wide; the 339-row agreement check documented.
- Staged file lints (column count, types, label regex).

## Log

- 2026-07-16: ticket created from survey.
- 2026-07-22: dependency updated T13 → T13+T30 (orchestrator). T13 found the enhanced-curve trace arm broken (never called, fails known answers) — see T30 and T13's Log. The **coarse arm (`JLDecomposition`) is validated 32/32 and ready**: a coarse-rows-only first pass of this ticket may run on T13 alone at David's discretion; enhanced rows wait for T30. T13 also shipped `data/cmfdata/cmfdata.txt` (level ≤ 2000, depth 1000 — covers all 339 coarse ground-truth rows) and the `JacobianData` intrinsic.

- 2026-07-22 (wave2-K-opus): **claimed with an ORCHESTRATOR-IMPOSED SCOPE REDUCTION for this pass.**
  This pass covers **only the 389 coarse X₀(D;N)-type rows** (via the validated `JLDecomposition`
  arm) plus the reusable python-side machinery (rank / genus_minus_rank / log_conductor /
  trace_hash). The **2,198 enhanced (deg μ > 1 / Aut-part / mixed-ramified N) rows are OUT of this
  pass by design**, deferred to a follow-up.
  **Rationale (logged per orchestrator):** (a) T07 proved the shipped deg-2 enhanced rows carry a
  *different* Pollack μ class than current code produces, so all deg μ > 1 enhanced rows will be
  **regenerated with a different μ after T08 lands** — decomposing them now would be wasted; (b)
  T30 REFUSES (loudly, never wrong numbers) the Aut-part-H rows and mixed-ramified N rows (e.g.
  D=6 N=6=2·3) pending an Eran decision on the AL-twisted trace formula vs re-adding AL signs to
  cmfdata; and T30 confirmed all 1,711 shipped enhanced "newforms" values are `{}` (nothing
  enhanced was ever shipped). The **coarse rows are stable under all pending changes** (their μ is
  trivial / deg 1, no Aut-part, X₀(D;N) family), so the coarse pass is safe to stage now. Branch
  `ticket/T14-jacobian-columns` stacked on T30's `ticket/T30-trace-formula` @ 9df143b.

- 2026-07-22 (wave2-K-opus): **COARSE PASS COMPLETE → review.** All 389 coarse rows populated, all four
  cross-checks pass, artifact staged + lint-clean. Branch `ticket/T14-jacobian-columns` (commits
  3b707eb, a7db46c, 920720f, 8d4a1c4 on top of T30 @ 9df143b). Nothing pushed; no DB writes.

  ### Coarse-row criterion (empirically derived + logged)
  **`autmuO_norms IS NULL`** ⟺ coarse X₀(D;N) row. Gives exactly **389 rows**, every one with
  `level=1 ∧ deg_mu=1 ∧ is_coarse=t`. Every enhanced row has `autmuO_norms` populated (a set like
  `{2,6,1}`); the coarse writer (`tablesX0DN.m`) leaves it `\N`. Cross-checked: the one enhanced row
  that also has non-NULL `dims` (`6.1.1.4.0.a.1`, genus 0, `dims={}`) is correctly excluded by the
  criterion, so the "339 populated" of the survey = 338 coarse + that 1 enhanced genus-0 row.
  Of the 389 coarse: **338 already had `newforms/dims/mults/conductor/rank/simple/squarefree/
  genus_minus_rank`** (but NULL `log_conductor/trace_hash/traces` — the old writer set those `\N`),
  **51 were entirely empty**, **2 are genus 0** (`10.1.1.4.0.a.1`, `22.1.1.4.0.a.1`).
  Congruence level N=1 for ALL coarse rows, so the "N" of X₀(D;N) is the **Eichler level M = discO/discB**;
  `JLDecomposition(discB, M, X : g:=genus)` is the call (AmbientLevel = discB·M = discO).

  ### What ran (coarse arm = validated `JLDecomposition`, NOT the enhanced trace-matching arm)
  1. **Magma** `code/jacobian_decomp/t14_coarse_driver.m` → `JLDecomposition` over all 389 rows
     (loads cmfdata once, ~0.1s; whole pass ~1 min). Fills newforms/mults/dims/conductor/rank/simple.
  2. **Python** `t14_python_pass.py` (`sage -python`, read-only db) → rank, genus_minus_rank,
     log_conductor, traces, trace_hash from `db.mf_newforms`, + the cross-checks.
  3. **Writer** `t14_write_update.py` → the staged artifact + invariant-key CSV.
  (`t14_export_coarse.py` pulls the rows; `t14_crosscheck_d.m` runs cross-check (d).)

  ### Column semantics — ALL derived empirically from `gps_gl2zhat_fine`, not guessed (Q13.1)
  - `conductor` = `Factorization(∏ level(f_i)^(mult_i·dim_i))`, stored `{{p,e},…}` (int4[][]).
  - `log_conductor` = **ln(conductor integer)** = Σ(mult·dim)·ln(level), stored to **21 sig figs**
    (matches modcurve exactly: ln(32)=`3.46573590279972654709`).
  - `rank` = Σ mult_i·analytic_rank(f_i) (Galois-orbit analytic rank). Range 0..8 over the coarse set.
  - `traces` = **168 values = a_p over the first 168 primes (p<1000)**, a_p(Jac)=Σ mult_i·a_p(f_i)
    (the `mf_newforms.traces` column at prime indices). Verified against modcurve's uniform 168-length.
  - `trace_hash` = **(Σ mult_i·trace_hash(f_i)) mod (2^61−1)** — the standard `lmfdb.utils.trace_hash`
    is GF(2^61−1)-linear in the a_p list, so the Jacobian hash is the multiplicity-weighted sum of the
    newforms' own `mf_newforms.trace_hash` (verified on modcurve rows 16.24.2.c.1 = additive, and
    16.48.2.p.1 = ×2 multiplicity — both exact). Uses TH_P = primes in [2^12,2^13); can NOT be read
    off the short `traces` column.
  - `simple` ⟺ single newform, mult 1 (genus>0). `squarefree` ⟺ all mults = 1.

  ### Cross-checks (ticket step 4) — ALL PASS
  - **(a) 338/338** recomputed rows match the shipped DB **exactly** (newforms, dims, mults, conductor,
    rank, simple, squarefree, genus_minus_rank). **Zero corrections needed** — the whole pipeline
    reproduces ground truth. (Match keyed by label AND validated invariant-wise.)
  - **(b) 389/389** Σ dims·mults = genus.
  - **(c) 389/389** simple ⟺ single-newform-mult-1 (genus-0 is the documented early-return special case).
    Independently, rank(python `mf_newforms`) == rank(Magma cmfdata) on **389/389**.
  - **(d)** X₀⁶(M) `traces` vs the T30 trace formula direct: `HTraces` (Borel-mod-M route) exactly
    matches the stored a_p at every good prime for M=5,7,11,13 (incl. the genus-3 X₀⁶(11), 3 newforms).
    Independent validation of the traces column: trace-formula ↔ newform-sum.

  ### NULL-with-reason tally (acceptance: all rows populated OR NULL-with-reason)
  - **trace_hash: 18 genus>0 rows NULL** because a constituent newform has **dim ≥ 21**, and LMFDB
    stores `mf_newforms.trace_hash` only for **dim ≤ 20** (verified: 100% present ≤20, 0% ≥21). These
    rows carry full newforms/dims/mults/conductor/rank/traces/log_conductor — only the hash is absent.
    Rows: 671/731/767/779/791/835/851/869/871/893/899/923/943/959/965/979/989/995 (all `.1.1.*.a.1`, N=1).
  - **2 genus-0 rows**: trivial-Jacobian encoding — newforms/dims/mults/conductor `{}`, rank 0,
    simple/squarefree t, genus_minus_rank 0, and log_conductor/trace_hash/traces `\N`.
  - **Everything else fully populated. 0 rows unresolved / 0 code −3 / 0 empty-genus>0.**
  - **Max candidate level needed = max discO = 998 < 2000** (dump bound), congruence N=1 ⇒ level = discO.
    The shipped `data/cmfdata/cmfdata.txt` (level≤2000, depth 1000) covers the entire coarse set;
    **no dump extension was required.** (Ticket step 3: max level = 998.)

  ### Genus-0 encoding — DECISION + flag for David
  The ticket says "copy modcurve's genus-0 encoding exactly", but modcurve's genus-0 convention is
  itself inconsistent (of 161,778 genus-0 modcurve rows: `dims`/`simple` are **always** NULL, yet
  `rank`/`genus_minus_rank` are set on 15,633 and `newforms`/`traces` on 2,137). The two shipped coarse
  genus-0 rows instead carry `JLDecomposition`'s own self-consistent early-return (empty arrays, rank 0,
  simple/squarefree true, gmr 0). **I kept that** (it is what the validated arm produces AND matches the
  shipped rows, so cross-check (a) stays green), and set only the three new columns
  (log_conductor/trace_hash/traces) to `\N` for genus 0. ⟐ David: if you'd rather mirror modcurve and
  NULL `dims`/`simple` for the 2 genus-0 rows, it's a 2-row edit — say the word.

  ### Artifacts (absolute paths) + LOAD COMMANDS
  - `shimcurve_tickets/artifacts/T14-jacobian-update.txt` — `update_from_file` format, **PROVISIONAL —
    pending T27 reload** banner, 12 cols (`label` + the 11 Jacobian columns), psycodict canonical
    col_type header, 389 data rows. **Lint-clean** (12-col, types == `db.col_type`, labels unique,
    trace_hash/traces/log_conductor re-verified on samples incl. the mult-2 curves 6.210/6.330).
  - `shimcurve_tickets/artifacts/T14-jacobian-keys.csv` — invariant re-key tuple
    (label,discB,discO,deg_mu,level,index,genus) per the BOARD PROVISIONAL rule.
  - **Load (after the T27 reload/relabel, with editor creds, from `~/claude/lmfdb`):**
    ```
    grep -v '^#' shimcurve_tickets/artifacts/T14-jacobian-update.txt > /tmp/t14load.txt
    # RE-KEY the label column first if T27 changed labels — join via T14-jacobian-keys.csv on
    # (discB,discO,deg_mu,level,index,genus); coarse labels are likelier-stable but the banner applies.
    from lmfdb import db
    db.gps_shimura_test.update_from_file('/tmp/t14load.txt', label_col='label', sep='|')
    ```
    (`label` is the table's `_label_col` and is unique 2587/2587, so the key is well-formed.)

  ### Flags for David (incl. production-cmfdata spec for the eventual enhanced pass)
  1. **`trace_hash` cap at dim 20 is LMFDB-wide, not a dump gap** — the eventual enhanced pass will hit
     the same NULL for any Jacobian with a dim≥21 constituent; not fixable by regenerating cmfdata.
  2. **The `traces` column (168 primes, needs a_997) is the real depth driver, not just the matcher.**
     T13 found `mf_newforms.traces` thins to ~100 coefficients for level ≳ 10000; the coarse set (level
     ≤ 998, ≥1000 traces) is safe, but enhanced rows whose newforms exceed level ~10000 will need
     extended a_p (from `mf_hecke_nf`) to fill the `traces` column, over and above the matcher's Sturm
     need. The production dump spec should guarantee ≥ 997 a_n (i.e. through p=997) for every form, plus
     the matcher's Sturm depth.
  3. Enhanced pass remains blocked per the scoping entry (T08 μ-regeneration; T30's refused Aut-part /
     mixed-ramified-N rows). This coarse artifact is independent of those and ready now.
  4. Reusable machinery for the enhanced pass is in place: the python pass's rank/traces/trace_hash/
     log_conductor logic is arm-agnostic (feed it any newform decomposition); only the Magma front-half
     swaps `JLDecomposition` → `JacobianData` (T30's enhanced arm).

  Files (my ownership): `code/jacobian_decomp/{t14_coarse_driver.m, t14_python_pass.py,
  t14_write_update.py, t14_export_coarse.py, t14_crosscheck_d.m}`, `tests/t14_jacobian_columns_test.py`.
  Touched NO T13/T30 machinery. Regression: `sage -python tests/t14_jacobian_columns_test.py` green
  (offline formula unit tests + end-to-end reproduction of 3 shipped rows).
