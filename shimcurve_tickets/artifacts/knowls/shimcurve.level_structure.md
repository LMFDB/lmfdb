title: Level structure of a Shimura curve
status: draft
db: no (new)
waits_on: —
note: >
  New; the long conceptual knowl (used 6x in the Level structure section of the page, and on
  the "generators" search column). Framework: LSSV arXiv:2308.15193 §3.5 (enhanced
  representations); consistent with the seeded shimcurve / shimcurve.enhanced_group knowls.
  Modelled on modcurve.level_structure.
---
Let $(O,\mu)$ be a {{KNOWL('shimcurve.polarized_order','polarized quaternion order')}}, let $G \colonequals \Aut_{\pm\mu}(O)\ltimes \widehat{O}^\times$ be the {{KNOWL('shimcurve.enhanced_group','enhanced semidirect product')}}, let $H\le G$ be an open compact subgroup of {{KNOWL('shimcurve.level','level')}} $N$, and let $A$ be a {{KNOWL('shimcurve.pqm','PQM')}} abelian surface over a {{KNOWL('nf','number field')}} $K$ whose geometric endomorphisms are identified with $O$ compatibly with the polarization $\mu$.

The $N$-torsion $A[N]$ is free of rank one over $O/NO$, and the reduction of the enhanced group,
    \[ G_N \colonequals \Aut_{\pm\mu}(O)\ltimes \modstar{O}{NO}, \]
acts on the set of enhanced trivializations of $A$ (the identification of $\operatorname{End}(A_{\overline K})$ with $O$ up to $\Aut_{\pm\mu}(O)$, together with an $O/NO$-basis of $A[N]$). An **$H$-level structure** on $A$ is an $H$-orbit $[\iota]_H$ of enhanced trivializations, where $H$ acts through its image in $G_N$.

An $H$-level structure is **rational** if its isomorphism class is stable under $\operatorname{Gal}_K$. The action of Galois on the enhanced structure is recorded by the **enhanced Galois representation**
    \[ \rho_A \colon \operatorname{Gal}_K \longrightarrow \Aut_{\pm\mu}(O)\ltimes \modstar{O}{NO} \]
of \cite{arxiv:2308.15193}. If $A$ admits a rational $H$-level structure, then the image of $\rho_A$ is contained in a conjugate of $H$, and the isomorphism class of the pair $\bigl(A,[\iota]_H\bigr)$ is a $K$-rational point on the {{KNOWL('shimcurve','Shimura curve')}} $X_H$.

For each Shimura curve $X_H$ we display generators of the ambient group $\Aut_{\pm\mu}(O)\ltimes \modstar{O}{NO}$ — each written as a pair consisting of an element of $N_{B^\times}(O)/\Q^\times$ and an element of the congruence part $\modstar{O}{NO}$ — together with the subgroup $H\le G_N$ itself.
