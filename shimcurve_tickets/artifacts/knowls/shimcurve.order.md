title: Quaternion order
status: final-candidate
db: yes (in DB, consistent — reproduced verbatim)
waits_on: —
note: Defines "maximal" inline; the separate id shimcurve.maximal (referenced by the X(D;N)-family knowls) is still missing — see shimcurve.maximal.md and the T26 Log.
---
Let $B$ be a {{KNOWL('shimcurve.quaternion_algebra','quaternion algebra')}} over $\Q$. An **order** $O\subset B$ is a
$\Z$-lattice in $B$ that is also a subring of $B$ (where we 
require $1 \in O$). We say that $O$ is **maximal** if it is 
not properly contained in another order of $B$.

Unlike {{KNOWL('nf.order','orders in number fields')}}, there 
is never a unique maximal order in a rational quaternion
algebra; however, the number of $B^\times$-conjugacy classes is finite (and in many cases, there is exactly one $B^\times$-conjugacy class).
