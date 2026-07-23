title: Elliptic curve of a point
status: needs-Q
db: no (new)
waits_on: (David) — meaning of the Elabel link for PQM points is not settled
note: >
  New, but FLAGGED. main.py:909 LinkCol("Elabel", "shimcurve.elliptic_curve_of_point",
  "Elliptic curve", url_for_EC/ECNF); the column appears in the (currently commented-out)
  points tables only when NOT contains_negative_one (fine curves). Points of a Shimura curve
  parametrize abelian SURFACES, so the association to an elliptic curve is not the modular-curve
  one and needs David's confirmation (candidate meanings: an isogeny factor of a
  non-geometrically-simple A; a CM elliptic curve for a CM point; or leftover modcurve
  boilerplate). Draft written conservatively; do NOT ship without the decision.
---
The **elliptic curve of a point** on a fine {{KNOWL('shimcurve','Shimura curve')}} $X_H$ (one for which $(1,-1)\notin H$) is the {{KNOWL('ec','elliptic curve')}} in the LMFDB naturally associated to the point, when such an association exists. {{TODO: pending David's decision — fix the precise correspondence between a point of $X_H$ and an elliptic curve for {{KNOWL('shimcurve.pqm','PQM')}} abelian surfaces (e.g. via an isogeny factor of a non-simple surface, or the CM elliptic curve of a {{KNOWL('shimcurve.cm_discriminants','CM point')}}). The displayed link uses the elliptic-curve label of that curve.}}
