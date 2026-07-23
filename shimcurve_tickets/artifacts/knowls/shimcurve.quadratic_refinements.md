title: Quadratic refinements
status: needs-Q
db: no (new)
waits_on: Q5 (fine/non-gerbiest level structures are out of v1 and their labelling is undecided)
note: >
  New. Backs the "Refinements" row (web_curve.py quadratic_refinements): for a coarse curve it
  lists the other database rows sharing its coarse_label; for a non-coarse curve it is "none".
  All v1 curves are coarse (Q5.2, Q12.2), so this row currently shows sibling coarse rows or
  "none in database". The precise fine-structure definition awaits Q5.3.
---
A **quadratic refinement** of a coarse {{KNOWL('shimcurve','Shimura curve')}} $X_H$ is a Shimura curve $X_{H'}$ with $H'\le H$ an index-two subgroup not containing $(1,-1)$, so that $\langle H',(1,-1)\rangle=H$ and $X_{H'}\to X_H$ is the corresponding fine cover; two refinements are recorded together when they share the same {{KNOWL('shimcurve.is_coarse','coarse')}} level structure. When $X_H$ itself is not coarse, it has no quadratic refinements.

{{TODO: pending Q5 decision — the non-gerbiest (fine) level structures are out of scope for the current release, and the labelling and precise classification of quadratic refinements (the meaning of the fine-label suffix) are not yet fixed. The displayed list currently shows only the sibling coarse curves stored under the same coarse label.}}
