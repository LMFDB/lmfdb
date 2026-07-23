title: Known points
status: final-candidate
db: no (new)
waits_on: —
note: New; adapts modcurve.known_points. Maps to the num_known_degree1_points / num_known_degree1_noncm_points columns.
---
The points on a {{KNOWL('shimcurve','Shimura curve')}} $X_H$ recorded in the database fall into two categories: {{KNOWL('shimcurve.cm_discriminants','CM points')}} and non-CM points (corresponding to {{KNOWL('shimcurve.pqm','PQM')}} abelian surfaces without complex multiplication). Unlike {{KNOWL('modcurve','modular curves')}}, a Shimura curve of {{KNOWL('shimcurve.discb','discriminant')}} $D>1$ has no cusps.

When searching, you can specify the number of known degree-one points (of any type) or the number of known non-CM degree-one points. In each case the count is the number of such points currently stored, which may be smaller than the actual number of points on the curve; in particular it is always finite, even for genus $0$ curves or positive-rank genus $1$ curves that have infinitely many rational points.
