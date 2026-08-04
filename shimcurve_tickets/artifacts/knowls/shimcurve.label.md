title: Label of a Shimura curve
status: draft
db: yes (NEEDS UPDATE — normative spec; supersedes the yhuang 2026-01-12 version)
waits_on: Q3 (Pollack class index) and Q11 (names) — TODO markers only; core grammar is implemented (T29)
note: >
  Documents the CURRENT implemented grammar (ShimCurve branch ticket/T29-label-determinism,
  in review). Verified against live rows: maximal `6.2.3.2.0.a.1` (7 comps),
  Eichler `15.30.1.1.4.3.a.1` (8 comps). Adds, over the current DB text: the explicit
  order_label form (maximal D vs Eichler discB.discO), the T29 tiebreak (AL content then
  canonical generators), and the psl2label/scalar_label side-labels. Two TODO markers for the
  pending Q3/Q11 extensions. Coordinate with T11 (fine/scalar labels) and main.py LABEL_RE.
---
Let $(O,\mu)$ be a {{KNOWL('shimcurve.polarized_order','polarized order')}} in an indefinite division {{KNOWL('shimcurve.quaternion_algebra','quaternion algebra')}} $B$ over $\Q$ of {{KNOWL('shimcurve.discb','discriminant')}} $D$, and let $H \le \Aut_{\pm\mu}(O)\ltimes \widehat{O}^\times$ be an open compact subgroup of the {{KNOWL('shimcurve.enhanced_group','enhanced semidirect product')}} of {{KNOWL('shimcurve.level','level')}} $N$. The **label** of the {{KNOWL('shimcurve', 'Shimura curve')}} $X_H$ has the form
\[ \mathtt{D.\delta.N.i.g.c.n} \qquad\text{or}\qquad \mathtt{D.d.\delta.N.i.g.c.n}, \]
where

- $D$ is the {{KNOWL('shimcurve.discb','discriminant')}} of $B$;
- $d$ is the {{KNOWL('shimcurve.disco', 'reduced discriminant')}} of $O$, present only when $O$ is not maximal (so that $\mathtt{D.d}$ is the label of an {{KNOWL('shimcurve.eichler','Eichler order')}} of level $M=d/D$, and $\mathtt{D}$ alone labels the maximal order, where $d=D$ is omitted);
- $\delta$ is the {{KNOWL('shimcurve.nrdmu','polarization degree')}} of $\mu$;
- $N$ is the {{KNOWL('shimcurve.level','level')}} of $H$;
- $i$ is the {{KNOWL('shimcurve.index', 'index')}} of $H$;
- $g$ is the {{KNOWL('shimcurve.genus', 'genus')}} of $X_H$;
- $c$ is a base-26 ordinal identifying the {{KNOWL('modcurve.gassmann_class','Gassmann class')}} of $H$ among subgroups of the same level, index, and genus, where two subgroups are in the same class when they have the same permutation character on the enhanced group (this makes their Jacobians isogenous);
- $n$ is a positive integer distinguishing nonconjugate subgroups of the same level, index, genus, and Gassmann class.

The leading part $\mathtt{D}$ or $\mathtt{D.d}$ is the label of the underlying {{KNOWL('shimcurve.order','quaternion order')}}, and $\mathtt{D.d.\delta}$ (resp. $\mathtt{D.\delta}$) is the label of the {{KNOWL('shimcurve.polarized_order','polarized order')}} $(O,\mu)$.

**Ordering within a Gassmann class.** The ordinal $n$ is assigned by an intrinsic total order on the subgroups of a class, so that labels are reproducible across regenerations: first by the **Atkin–Lehner content** of $H$ (the set of Hall divisors $m\parallel DM$ with $w_m\in H$), and, if still tied, by a canonical normal form of the generators of $H$ (the lexicographically minimal generating sequence over the conjugacy class of $H$, in the style of the modular-curve canonical generators).

**Associated side-labels.** Alongside the curve label, each row stores:

- the label $\mathtt{N.i.g.c.n}$ of the underlying enhanced level structure with the order and polarization data removed (used to identify the coarse structure);
- a $\mathrm{PSL}_2$-label recording the image of $H$ in the norm-one (Fuchsian) part $\Aut_{\pm\mu}(O)\ltimes\modstar{O}{NO}^{1}$; Shimura curves with the same $\mathrm{PSL}_2$-label share the same {{KNOWL('portrait.shimcurve','picture')}};
- a scalar label recording the image of $H$ under the reduced norm in $\modstar{\Z}{N\Z}$.

{{TODO: pending Q3 decision — polarizations are not unique in a given degree; they are classified by Pollack conjugation ($\mu_1\sim\bar\alpha\mu_2\alpha$, $\alpha\in O^\times$), so a canonically-ordered Pollack-class index will be appended to the polarization component $\delta$, lengthening the label by one component. The exact placement and the class ordering are not yet fixed (Rotger, Crelle 561 (2003); coordinate with the frontend LABEL_RE).}}

{{TODO: pending Q11 decision — the human-readable {{KNOWL('shimcurve.standard','name')}} grammar (e.g. $X(D,M;N)$, $X^*(D,M)$, decoration for $\delta>1$) is still under discussion and is independent of the label above.}}
