title: Modular cover
status: draft
db: no (new)
waits_on: —
note: >
  New; the single most-referenced knowl (14x — the "Modular covers", "Modular covered by",
  and fiber-product sections). Modelled on modcurve.modular_cover, adapted to the enhanced
  group and the Fuchsian (norm-one) index.
---
Each inclusion of open compact subgroups $H\le G$ of the {{KNOWL('shimcurve.enhanced_group','enhanced group')}} $\Aut_{\pm\mu}(O)\ltimes\widehat{O}^\times$ induces a morphism of {{KNOWL('shimcurve','Shimura curves')}} $X_H\to X_G$: every {{KNOWL('shimcurve.pqm','PQM')}} abelian surface with a level-$H$ structure has an underlying level-$G$ structure. We call such a morphism a **modular cover**.

The **degree** of $X_H\to X_G$ equals the ratio of the Fuchsian (norm-one) indices of $H$ and $G$ — the index of the image of $\pm H\cap\Gamma$ over that of $G$ in the norm-one group $\Gamma$. As with modular curves, when $(1,-1)$ lies in $G$ but not $H$ the inclusion $H<G$ can be strict while the induced map $X_H\to X_G$ has degree $1$.

A modular cover is **minimal** if $H<G$ is a maximal proper subgroup.

The morphism $X_H\to X_G$ induces a surjection $\phi\colon \operatorname{Jac}(X_H)\to\operatorname{Jac}(X_G)$; the **kernel** of the modular cover is the connected component of $\ker\phi$, an {{KNOWL('ag.abelian_variety','abelian variety')}} that may have {{KNOWL('ag.dimension','dimension')}} zero.
