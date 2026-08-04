title: Isogeny decomposition of the Jacobian of a Shimura curve
status: final-candidate
db: yes (in DB, consistent — reproduced verbatim)
waits_on: —
note: Semantics confirmed by Q13.1 / T13 / T30 (Jacquet–Langlands: Jac(X_H) is isogenous to a product of modular abelian varieties attached to the weight-2 newforms in the D-new subspace).
---
As with any {{KNOWL('ag.abelian_variety', 'abelian variety')}}, the {{KNOWL('ag.jacobian', 'Jacobian')}} $J_H$ of a {{KNOWL('shimcurve', 'Shimura curve')}} $X_H$ can be {{KNOWL('av.decomposition','decomposed')}} into {{KNOWL('av.simple', 'simple')}} {{KNOWL('av.isogeny','isogeny factors')}}.  For Shimura curves, these simple isogeny factors are modular abelian varieties corresponding to {{KNOWL('cmf.galois_orbit', 'Galois orbits')}} of {{KNOWL('cmf.weight', 'weight')}} 2 {{KNOWL('cmf.newform', 'newforms')}}.

We list two types of information about the **isogeny decomposition** of $J_H$:

- the multiset of dimensions of the simple isogeny factors: $1^3\cdot 2^2$ denotes $3$ factors of {{KNOWL('ag.dimension', 'dimension')}} $1$ and $2$ factors of dimension $2$;
- the multiset of newforms corresponding to the modular abelian varieties in the isogeny decomposition, listed by {{KNOWL('cmf.label', 'label')}}: $\texttt{11.2.a.a}^3\cdot \texttt{13.2.e.a}^2$ denotes five simple isogeny factors, three isogenous to the modular abelian variety corresponding to the newform labelled $\texttt{11.2.a.a}$ and two isogenous to the modular abelian variety corresponding to the newform labelled $\texttt{13.2.3.a}$.

When $X_H$ has {{KNOWL('modcurve.genus', 'genus')}} zero, $J_H$ is the trivial abelian variety of dimension zero, and no isogeny decomposition information is listed.
