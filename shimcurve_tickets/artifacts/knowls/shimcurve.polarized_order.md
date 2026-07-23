title: Polarized quaternion order
status: final-candidate
db: yes (in DB, consistent — reproduced verbatim)
waits_on: —
---
Let $O$ be an {{KNOWL('shimcurve.order','order')}} in an indefinite 
division {{KNOWL('shimcurve.quaternion_algebra','quaternion 
algebra')}} $B$ over $\Q$. Let $\operatorname{trd} : B \to \Q$
be the reduced trace. A **polarization** of $O$ is an element 
$\mu \in B^\times$ such that $\mu^2 \in \Z_{<0}$ and for all 
$x \in O$, we have $\operatorname{trd}(\mu x) \in \Z$.

A **polarized order** is a pair $(O,\mu)$ where $O$ is an 
order in an indefinite division quaternion algebra $B$ over 
$\Q$ and $\mu \in B^\times$ is a polarization of $O$.
