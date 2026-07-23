title: Analytic rank
status: final-candidate
db: yes (in DB, consistent — reproduced verbatim)
waits_on: —
note: Parallels rcs/modcurve.rank exactly; semantics confirmed by Q13.1 / T14 (rank = Σ mult·analytic_rank of the newform orbits).
---
The **analytic rank** of a {{KNOWL('shimcurve','Shimura curve')}} is the order of vanishing of its {{KNOWL('lfunction','L-function')}} at its {{KNOWL('lfunction.central_point','central point')}}, which is equal to the sums of the {{KNOWL('cmf.analytic_rank','analytic ranks')}} of the {{KNOWL('cmf.lfunction','L-functions')}} of the {{KNOWL('av.simple', 'simple')}} modular {{KNOWL('ag.abelian_variety','abelian varieties')}} corresponding to {{KNOWL('cmf.galois_orbit','Galois orbits')}} of {{KNOWL('cmf.newform','modular forms')}} that are the {{KNOWL('av.decomposition', 'isogeny factors')}} of its {{KNOWL('ag.jacobian', 'Jacobian')}}.

The {{KNOWL('ec.bsdconjecture', 'Birch and Swinnerton-Dyer')}} conjecture for modular abelian varieties implies that the analytic rank is equal to the {{KNOWL('ag.mordell_weil', 'Mordell-Weil rank')}} of the Jacobian.
