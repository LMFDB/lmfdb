title: Completeness of the Shimura curve database
status: needs-Q
db: yes (NEEDS UPDATE)
waits_on: Q12.4 (final completeness claim DEFERRED by Eran)
note: >
  Updated to the honest current coverage from the BOARD data-state snapshot (2,198 enhanced
  D=6 rows: δ ∈ {1,2,6}, N ∈ {1,2,3,4,6}; 389 coarse X_0(D;N) rows). The existing DB text omits
  N=1 and the δ ∈ {1,2,6} range and only mentions the D=6 coarse levels. The FINAL completeness
  statement (the discO ≤ 1000, N ≤ 6, all admissible squarefree δ target) is deferred per Q12.4
  — TODO marker. N=5 to be added after the T10 assertion fix.
---
The database currently contains data on the following {{KNOWL('shimcurve','Shimura curves')}}.

Coarse curves $X_0(D;N)$ and their Atkin–Lehner quotients:

- $X(D;1)=X_0(D;1)$ for every squarefree {{KNOWL('shimcurve.discb','discriminant')}} $D\le 1000$;
- $X_0(D;N)$ and their Atkin–Lehner quotients for a range of {{KNOWL('shimcurve.eichler','Eichler')}} levels with $D\cdot N\le 400$ and $N\le 65$, over twelve discriminants.

Enhanced curves $X_H$ (all {{KNOWL('shimcurve.is_coarse','coarse')}}, with surjective reduced norm) for the maximal {{KNOWL('shimcurve.order','order')}} of {{KNOWL('shimcurve.disco','reduced discriminant')}} $6$:

- all such $H\le\Aut_{\pm\mu}(O)\ltimes\modstar{O}{NO}$ with {{KNOWL('shimcurve.nrdmu','polarization degree')}} $\delta\in\{1,2,6\}$ and {{KNOWL('shimcurve.level','level')}} $N\in\{1,2,3,4,6\}$.

The {{KNOWL('shimcurve.decomposition','isogeny decomposition')}} of the {{KNOWL('ag.jacobian','Jacobian')}}, the {{KNOWL('shimcurve.rank','analytic rank')}}, and exact {{KNOWL('shimcurve.gonality','gonalities')}} are currently available for the coarse curves; for the enhanced curves these are being populated.

{{TODO: pending Q12.4 — the completeness claim for the full release (all $X_H$ for orders of reduced discriminant at most $1000$, level $N\le 6$, and every admissible squarefree polarization degree) is deferred until the generation run is complete; this statement will be updated to the exact range then achieved.}}
