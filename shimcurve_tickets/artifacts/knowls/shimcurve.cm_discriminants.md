title: CM points
status: draft
db: no (new)
waits_on: —
note: >
  New. Data status per Q9/T15: the cm_discriminants column is currently unpopulated for most
  rows; a v1 pass sets it from RationalCMPointsX0DN / RationalCMQuotientsX0DN for coarse rows.
  Definition (CM point on a Shimura curve = surface whose QM order admits an imaginary
  quadratic CM order) is standard (Voight, Quaternion Algebras, Ch. 43).
---
A **CM point** on a {{KNOWL('shimcurve','Shimura curve')}} $X_H$ is a point whose associated {{KNOWL('shimcurve.pqm','PQM')}} abelian surface has {{KNOWL('ag.complex_multiplication','complex multiplication')}}: equivalently, the underlying {{KNOWL('shimcurve.order','quaternion order')}} $O$ admits an optimal embedding of an {{KNOWL('nf.order','imaginary quadratic order')}} $S$, and the abelian surface is isogenous to the square of a CM elliptic curve. The **CM discriminant** of the point is the discriminant of $S$.

The CM points of a given discriminant $\Delta<0$ are defined over the ring class field attached to $\Delta$; those defined over $\Q$ (or a specified field) are listed on the curve's page. Because a Shimura curve of {{KNOWL('shimcurve.discb','discriminant')}} $D>1$ has no cusps, CM points play the role that cusps and CM points together play for {{KNOWL('modcurve','modular curves')}}.
