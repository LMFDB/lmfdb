# Decision register — David's verdicts

The authoritative record of sign-offs. Numbering follows [REVIEW_PACKET.md](REVIEW_PACKET.md)
(D1–D26) and its 2026-08-01 extension (D27–D57, the tickets that landed in review after the
packet plus the standing cross-cutting votes). **Agents: read this before acting on any ticket
Log that says "flag for David" — the answer may already be here.**

Status key: **DECIDED** = acted on / actionable now. *(no entry)* = still open, treat the
ticket's flag as live.

---

## Round 1 — 2026-08-01 (10 of 57)

| # | Ticket | Verdict | Consequence |
|---|--------|---------|-------------|
| **D3** | T29 | **Bless the fix** — `is_split` := "some conjugate of H splits against the standard section" | The representative-dependent computation is retired. Values change on a handful of rows; lands with the T27 reload. |
| **D4** | T29 | **Bless** — `G1` := kernel of the reduced-norm determinant hom on G | `psl2label` changes on 2158/2198 rows (98%), `scalar_label` follows. The 304 `shimcurve_pictures` rows re-key at reload (see D5). |
| **D5** | T29 → T27 | **Approved** — T27 is a full atomic `copy_from` reload with the rename; re-key the pictures | **Formal Q15.3 sign-off.** Label-keyed `update_from_file` against the current table is permanently off the table. Every `PROVISIONAL` artifact stays parked until T27 executes. |
| **D7** | T07 | **Approve as-is** — `gerbiness` := #ker(f), `base_gerbiness` added, schema grows; **`aut_gerbiness` keeps its name** (the `aut_band` rename option is declined) | The 69-col `?` / 71-col `\|` writer delta is blessed. Q2.2 is closed: no renames. |
| **D20** | T03 / T24 | **Full label** — `shimcurve_points.Clabel`/`curve_label` store `mu_label.coarse_label` | T03's staged files are already keyed correctly — **no re-key needed**. T24 gets the frontend follow-up (done 2026-08-01, see below). |
| **D25** | T24 | **Approve — merge + push** | Executed 2026-08-01 after the D20 + D26 follow-ups landed on the branch. |
| **D26** | T24 / T04 / T27 | **Add the column** — `factorization text[]` joins the canonical schema | Frontend references stay. Canonical schema 71 → **72 columns**. Needs `db.gps_shimura_test.add_column("factorization", "text[]")` at T27, alongside `base_gerbiness`. Populated at T27. |
| **D31** | T08 → T27 | **Approve the cascade as proposed** — one row per negation pair {[μ],[−μ]}; label shape `discB.discO.deg.i`; index i from the canonical class order | `mu_label` gains a component and the curve label follows; frontend `LABEL_RE` widens. **Not implemented anywhere yet** — this is now a scheduled T27-time work item (see below). Coordinates with Q11 (D54–56, open) and Q15. |
| **D46** | T15 / T06 / T27 | **Congruence level** — the level-family columns are computed from the congruence level, not the Eichler level M | The unified writers as landed are correct; the 71 + 86 + 303 devmirror rows T25 flagged self-heal at the T27 reload. No writer change. |
| **D48** | T25 → T06 | **Confirmed** — `quaternion_orders.discB`/`discO` are swapped on all 640 Eichler rows; **fix under T06 before the T27 reload** | T06 owns the fix. Area is unaffected (computed from the true discB), so Gauss–Bonnet stays green. |

### What round 1 did *not* settle

Still open, so the corresponding ticket flags remain live: **D1, D2** (T28/T29 approve-work),
**D6, D8–D12** (T10/T07/T09), **D13–D19, D21** (legacy data), **D22–D24** (T13),
**D27–D30, D32–D45, D47, D49–D53** (the post-packet tickets), **D54–D57** (Q11 name votes ×3,
Q14 `area` rename).

Consequences of the gaps worth knowing:

- **T29 and T07 cannot close.** Their semantic calls (D3/D4/D5, D7) are blessed, but the
  approve-work items (D2, D8–D11) are open, so both stay `status: review`.
- **T18 (names) stays blocked** on the Q11 votes (D54–56); **T06's `area` half stays blocked**
  on Q14 (D57) even though its discB/discO half (D48) is now green-lit.
- **The enhanced Jacobian pass stays blocked** on D43 (Aut-part trace route — Eran's call).
- **D49** (`nrd_mu` semantics) still gates the polarized-order schema doc and knowl.

---

## Actions taken on these verdicts (2026-08-01)

1. **T24 follow-ups + push** (D20, D25, D26) — the frontend now keys `shimcurve_points`,
   `shimcurve_modelmaps` and the coarse links on the **full** label via a single
   `full_coarse_label` attribute; `factorization` references kept per D26. Merged current
   `shimura_curves` and pushed. See T24's Log.
2. **T04 schema** (D26) — `factorization text[]` added to `GpsShimuraSchema()`; canonical
   schema is now 72 columns. See T04's Log.
3. **QUESTIONS.md** — Q15's three "still open for David" bullets closed (D3/D4/D5);
   Q2.2 closed (D7); Q3's cascade ⟐ closed (D31).
4. **T27** — reload checklist updated with the two `add_column` calls, the pictures re-key,
   the D31 label cascade, and the D48 prerequisite.

---

## Where the numbering comes from

D1–D26 are defined in [REVIEW_PACKET.md](REVIEW_PACKET.md). D27–D57 were assigned on
2026-08-01 when the nine post-packet review tickets (T04, T05, T08, T11, T14, T19, T20, T25,
T26, T30) and the standing Q11/Q14 votes were folded into one decision surface; the full text
of each lives in the interactive review document and is reproduced per-ticket in the Logs.
