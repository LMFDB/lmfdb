title: Is coarse
status: draft
db: yes (NEEDS UPDATE)
waits_on: —
note: >
  Encodes Q5.1's DECIDED criterion is_coarse ⟺ (1,−1) ∈ H (matches the frontend
  boolean `contains_negative_one`, main.py:294,605). The CURRENT DB text uses a
  STRONGER condition — "H contains the projection of ker(f)" (i.e. H ⊇ proj(KG)).
  Since KG ⊇ ⟨(1,−1)⟩, that implies (1,−1) ∈ H but is not equivalent in general;
  the two coincide on all released (gerbiest) data (Q5.2) but the go-forward
  criterion is (1,−1) ∈ H. Recommend replacing the DB text with the body below.
  Reconciliation flagged for David/T11.
---
Let $(O,\mu)$ be a {{KNOWL('shimcurve.polarized_order','polarized quaternion order')}} and let $H\le\Aut_{\pm\mu}(O)\ltimes\modstar{O}{NO}$ be an open compact subgroup of {{KNOWL('shimcurve.level','level')}} $N$. Write $-1$ for the image in the {{KNOWL('shimcurve.enhanced_group','enhanced group')}} of $-1\in O^\times$, so that $(1,-1)$ denotes the enhanced element that acts as multiplication by $-1$; this is the automorphism carried by every polarized abelian surface.

We say that $H$, and the associated {{KNOWL('shimcurve','Shimura curve')}} $X_H$, is **coarse** if $(1,-1)\in H$.

This is the direct analogue of the condition $-I\in H$ for {{KNOWL('modcurve','modular curves')}}. Because the $\pm1$ automorphism of a polarized abelian surface is absorbed into the "$\pm$" of $\Aut_{\pm\mu}(O)$, the element $(1,-1)$ acts trivially on the coarse moduli space; when it lies in $H$ the curve $X_H$ is the coarse space of its moduli stack $\mathfrak{X}_H$. When $H$ is not coarse, $X_H$ is a {{KNOWL('shimcurve.quadratic_refinements','quadratic refinement')}} of, and maps to, the coarse curve $X_{\langle H,(1,-1)\rangle}$.

Equivalently, $(1,-1)$ always lies in the kernel of the map $f\colon \Aut_{\pm\mu}(O)\ltimes O^{\times}\to N_{B^{\times}}(O)/\Q^{\times}$ given by $(w,x)\mapsto w\cdot x$, so $H$ is coarse if and only if it contains the reduction of $(1,-1)$ modulo $N$.
