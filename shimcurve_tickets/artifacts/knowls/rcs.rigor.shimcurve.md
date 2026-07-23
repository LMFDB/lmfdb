title: Reliability of Shimura curve data
status: draft
db: yes (NEEDS UPDATE — expands the one-line DB version)
waits_on: —
note: >
  Expands the existing one-sentence DB text with what is proven vs computed and the alpha-state
  label caveat (Q15.3 / T29: labels will change on the next reload). Keeps the "use with caution"
  disclaimer.
---
None of the data in the Shimura curves database depends on any heuristics or unproven conjectures, but it is still in an early **alpha** state and should be regarded as provisional — **use with caution!**

The {{KNOWL('shimcurve.genus','genus')}}, {{KNOWL('shimcurve.index','index')}}, and {{KNOWL('shimcurve.elliptic_points','elliptic point')}} counts are computed from exact formulas (Riemann–Hurwitz / Gauss–Bonnet and Ogg's signature formulas) and cross-checked for internal consistency. The {{KNOWL('shimcurve.decomposition','isogeny decompositions')}} of the Jacobians are computed via the Jacquet–Langlands correspondence and validated against independently known cases. Exact {{KNOWL('shimcurve.gonality','gonalities')}} for the coarse curves come from the published literature; for the remaining curves only gonality bounds are given.

Several columns are only partially populated: information on {{KNOWL('shimcurve.local_obstruction','local obstructions')}}, {{KNOWL('shimcurve.cm_discriminants','CM points')}}, {{KNOWL('shimcurve.known_points','known points')}}, and exact gonalities of the enhanced curves is incomplete, and **the absence of listed points should not be taken to mean that none exist**.

Because the database is in alpha, the {{KNOWL('shimcurve.label','labels')}} of Shimura curves may still change: the canonical ordering used to assign labels was revised, and the next data reload will relabel the table accordingly.
