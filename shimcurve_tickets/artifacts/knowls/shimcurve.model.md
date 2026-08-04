title: Models of a Shimura curve
status: final-candidate
db: no (new)
waits_on: —
note: New; adapts modcurve.model. Model types present in the module: canonical (0), plane (±2), Weierstrass (5), embedded (7); the base X(D;1) may be genus 0 (P^1).
---
There are several types of models of a {{KNOWL('shimcurve','Shimura curve')}} $X_H$, including

- {{KNOWL('shimcurve.plane_model','Plane models')}} (which may be smooth or singular),
- {{KNOWL('ag.canonical_model','Canonical models')}} (for non-hyperelliptic curves of genus at least $3$),
- {{KNOWL('shimcurve.embedded_model','Embedded models')}} (for hyperelliptic curves and curves of low genus),
- {{KNOWL('ag.hyperelliptic_curve','Weierstrass models')}} (for hyperelliptic and elliptic curves).

Unlike {{KNOWL('modcurve','modular curves')}}, a Shimura curve of {{KNOWL('shimcurve.discb','discriminant')}} $D>1$ has no cusps, so these models are computed from spaces of quaternionic modular forms rather than from $q$-expansions.
