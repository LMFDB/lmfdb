title: Fiber product
status: final-candidate
db: no (new)
waits_on: —
note: >
  New; the template's fiber-product paragraph currently links modcurve.fiber_product (line 369),
  but shimcurve.fiber_product is on the T26 list and referenced (main.py:770, commented). Adapts
  modcurve.fiber_product to the level-one base.
---
A {{KNOWL('shimcurve','Shimura curve')}} $X_H$ is a **fiber product** of Shimura curves $X_{H_1},\dots,X_{H_k}$ over the level-one base curve $X(D;1)$ if the {{KNOWL('shimcurve.modular_cover','modular covers')}} $X_H\to X_{H_i}$ exhibit $X_H$ as the fiber product $X_{H_1}\times_{X(D;1)}\cdots\times_{X(D;1)}X_{H_k}$; group-theoretically this holds when $H=H_1\cap\cdots\cap H_k$ inside the {{KNOWL('shimcurve.enhanced_group','enhanced group')}} and the $H_i$ pairwise generate it. Fiber products let a Shimura curve be built from simpler covers and can be searched for using the jump box by joining curve names or labels with $*$.
