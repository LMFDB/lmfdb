title: Enhanced group associated to a polarized quaternion order
status: final-candidate
db: yes (in DB, consistent — reproduced verbatim)
waits_on: —
note: Not on the T26 id list, but referenced by shimcurve.level/index/label/level_structure etc.; included so the cross-reference graph is complete. This is the LSSV §3.5 enhanced semidirect product.
---
Let $(O,\mu)$ be a {{KNOWL('shimcurve.polarized_order',
'polarized quaternion order')}}.
We define $\widehat{O} \colonequals O\otimes_\Z \widehat{\Z}$. Then 
$\widehat{O}^\times$ is a {{KNOWL('gl2.profinite', 'profinite group')}} with
    \[ \widehat{O}^\times = \lim_{\xleftarrow[N]{}} \modstar{O}{NO}, \]
where $N$ ranges over all positive integers. We define
    \[ \Aut_{\pm\mu}(O) \colonequals \{\gamma \in N_{B^\times}(O)/\Q^\times :
        \gamma^{-1}\mu\gamma = \pm \mu\}. \]
Then $\Aut_{\pm\mu}(O)$ acts on $\widehat{O}^\times$.
The **enhanced group (associated to $(O,\mu)$)** is
the semidirect product 
$\Aut_{\pm\mu}(O)\ltimes \widehat{O}^\times$.
