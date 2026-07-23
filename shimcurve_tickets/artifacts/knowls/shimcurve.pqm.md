title: Potential quaternionic multiplication
status: draft
db: no (new)
waits_on: —
note: >
  New. Used on the browse/statistics pages (main.py:1067,1075: "abelian surfaces A/Q with
  potential quaternionic multiplication"). Definition from LSSV arXiv:2308.15193 (an abelian
  surface A/F is O-PQM if End(A_{F̄}) ≃ O is a maximal order in a nonsplit quaternion algebra).
---
An {{KNOWL('ag.abelian_variety','abelian surface')}} $A$ over a field $F$ has **quaternionic multiplication** if its endomorphism ring $\operatorname{End}(A)$ is an {{KNOWL('shimcurve.order','order')}} in an indefinite {{KNOWL('shimcurve.quaternion_algebra','quaternion algebra')}} $B$ over $\Q$. It has **potential (or potentially) quaternionic multiplication (PQM)** if the {{KNOWL('ag.base_change','base change')}} $A_{\overline{F}}$ to an algebraic closure has quaternionic multiplication — that is, the geometric endomorphism ring $\operatorname{End}(A_{\overline{F}})$ is such an order $O$ — even when the quaternionic endomorphisms are not all defined over $F$.

When $\operatorname{End}(A_{\overline{F}})$ is a maximal order in a nonsplit $B$, the surface $A_{\overline{F}}$ is simple; these are the abelian surfaces studied in \cite{arxiv:2308.15193}. A {{KNOWL('shimcurve.polarized_order','polarization')}} $\mu$ of $O$ equips $A$ with a principal polarization, and the {{KNOWL('shimcurve','Shimura curve')}} $X_H$ is the moduli space of PQM abelian surfaces carrying this polarization together with an {{KNOWL('shimcurve.level_structure','$H$-level structure')}}: a point of $X_H$ over a number field $K$ corresponds to such a surface for which the level structure is $K$-rational.
