title: Endomorphism field Galois group
status: draft
db: no (new)
waits_on: —
note: >
  New. Backs the "Endomorphism field Galois group" row (web_curve.py show_galendgroup,
  galEnd column, rendered as an abstract group knowl). Interpretation from the enhanced
  representation (LSSV §3.5): the projection of ρ_A to Aut_{±μ}(O) records the Galois action
  on the geometric endomorphisms. Confirm phrasing with David.
---
Let $A$ be a {{KNOWL('shimcurve.pqm','PQM')}} abelian surface over a number field $K$ corresponding to a point of the {{KNOWL('shimcurve','Shimura curve')}} $X_H$. The geometric endomorphism ring $\operatorname{End}(A_{\overline K})\cong O$ is in general not defined over $K$; the **endomorphism field** is the minimal extension $L/K$ over which every element of $\operatorname{End}(A_{\overline K})$ is defined. It is a Galois extension, and the **endomorphism field Galois group** is $\operatorname{Gal}(L/K)$.

Equivalently, composing the enhanced {{KNOWL('shimcurve.level_structure','Galois representation')}} $\rho_A$ with the projection $\Aut_{\pm\mu}(O)\ltimes\modstar{O}{NO}\to\Aut_{\pm\mu}(O)$ gives the action of $\operatorname{Gal}_K$ on $\operatorname{End}(A_{\overline K})$; the endomorphism field is the fixed field of its kernel, and the Galois group is the image.
