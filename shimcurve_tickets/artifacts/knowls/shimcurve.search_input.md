title: Look up a Shimura curve by label or name
status: needs-Q
db: no (new)
waits_on: Q11 (the name grammar — three votes still open)
note: >
  New; the jump-box knowl (main.py:655, jump_knowl). Documents the CURRENTLY accepted input
  forms (LABEL_RE, NAME_RE, parse_family, fiber products via *). The name grammar itself is
  Q11 (open), so the accepted names may broaden — TODO marker.
---
The search box accepts any of the following:

- a {{KNOWL('shimcurve.label','label')}} of a {{KNOWL('shimcurve','Shimura curve')}}, e.g. $\texttt{6.1.1.4.0.a.1}$;
- a {{KNOWL('shimcurve.standard','standard name')}}, e.g. $X(6;1)$, $X(6,1)$, $X(D;N)$, $X(D,M;N)$, or an Atkin–Lehner quotient $X^*(D;N)$ (a comma may be used in place of the semicolon on input);
- a {{KNOWL('shimcurve.fiber_product','fiber product')}} of the above, written by joining names or labels with $*$.

{{TODO: pending Q11 decision — the systematic {{KNOWL('shimcurve.standard','name')}} grammar (the second slot $M$ vs $D\cdot M$, partial Atkin–Lehner notation, and whether polarization degree $\delta>1$ appears in names) is still being decided; the set of names the box accepts will be finalized once that is settled (the underlying regular expressions in the module are $\texttt{LABEL\_RE}$ and $\texttt{NAME\_RE}$).}}
