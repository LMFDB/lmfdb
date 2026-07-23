title: Torsion subgroup
status: draft
db: no (new)
waits_on: —
note: >
  New. Backs the "Torsion subgroup" row (web_curve.py show_torsion, torsion column, displayed
  as ⊕ Z/tZ). Interpreted as the rational torsion forced by the H-level structure, in the
  spirit of LSSV arXiv:2308.15193 (rational torsion of QM abelian surfaces is 12-torsion of
  order ≤ 18). Confirm phrasing/exact meaning with David.
---
The **torsion subgroup** attached to a {{KNOWL('shimcurve','Shimura curve')}} $X_H$ is the group structure of the rational torsion carried by the {{KNOWL('shimcurve.pqm','PQM')}} abelian surfaces it parametrizes: the subgroup of the $N$-torsion determined by the $H$-{{KNOWL('shimcurve.level_structure','level structure')}}, displayed as a direct sum $\bigoplus_i \Z/t_i\Z$. For an abelian surface $A/\Q$ whose geometric endomorphism ring is a maximal order in a nonsplit quaternion algebra, the rational torsion subgroup of $A(\Q)$ is annihilated by $12$ and has order at most $18$ \cite{arxiv:2308.15193}.
