title: Source of Shimura curve data
status: draft
db: no (new)
waits_on: —
note: >
  New. Honest provenance grounded in BOARD + the ShimCurve library and the ticket work
  (T07/T13/T19/T30). CONTRIBUTOR LIST IS A TODO for David to finalize — I have named only the
  package/paper authors that are clear from the repos; do not ship the acknowledgement without
  David's curation.
---
The Shimura curves database was computed with the <a href="https://github.com/assaferan/ShimCurve">ShimCurve</a> Magma package, which implements {{KNOWL('shimcurve.level_structure','enhanced level structures')}} on {{KNOWL('shimcurve.order','quaternion orders')}} following the framework of Laga, Schembri, Shnidman, and Voight \cite{arxiv:2308.15193}.

Some of the key algorithms that were used include:

- enumeration of the {{KNOWL('shimcurve.is_coarse','coarse')}} subgroups $H\le\Aut_{\pm\mu}(O)\ltimes\modstar{O}{NO}$ of the {{KNOWL('shimcurve.enhanced_group','enhanced group')}}, with a canonical ordering used to assign {{KNOWL('shimcurve.label','labels')}};
- computation of the {{KNOWL('shimcurve.genus','genus')}} and {{KNOWL('shimcurve.elliptic_points','elliptic points')}} via the Riemann–Hurwitz and Gauss–Bonnet formulas and Ogg's signature formulas for Atkin–Lehner quotients;
- the {{KNOWL('shimcurve.decomposition','isogeny decomposition')}} of the {{KNOWL('ag.jacobian','Jacobian')}} via the Jacquet–Langlands correspondence and the Eichler–Selberg trace formula (Voight, <i>Quaternion Algebras</i>, Ch. 30);
- {{KNOWL('shimcurve.gonality','gonality')}} bounds for the coarse curves $X_0(D;N)$ from the published tables of Ogg, Gonz&aacute;lez–Rotger, Rotger, and Padurariu–Saia.

{{TODO: David to finalize the list of contributors and the acknowledgement of the workshops/funding under which the data was produced.}}
