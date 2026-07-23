title: Local obstruction
status: final-candidate
db: yes (in DB, consistent — reproduced verbatim)
waits_on: —
note: Semantics match modcurve (Q9). Data: obstructions/pointless are currently unpopulated for most rows; a v1 pass encodes Shimura's D>1 real-point obstruction (0 ∈ obstructions) for coarse X_0(D;N) — see Q9, T15.
---
A {{KNOWL('shimcurve', 'Shimura curve')}} $X_H/\Q$ has a **local obstruction** (to rational points) if it has no real points, or if it has no $\Q_p$-points for some prime $p$.

When $X$ has {{KNOWL('shimcurve.genus', 'genus')}} $0$ the absence of local obstructions guarantees the existence of rational points, but this is not true in general.
