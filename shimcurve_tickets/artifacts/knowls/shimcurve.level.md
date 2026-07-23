title: Level of a Shimura curve
status: final-candidate
db: yes (in DB, consistent — reproduced verbatim)
waits_on: —
---
Let $(O,\mu)$ be a {{KNOWL('shimcurve.polarized_order',
'polarized quaternion order')}}, and let 
$G \colonequals \Aut_{\pm\mu}(O)\ltimes \widehat{O}^\times$ be the corresponding
{{KNOWL('shimcurve.enhanced_group','enhanced semidirect product')}}.
Let $H \le G$ be an open compact subgroup. The **level** of 
$H$ is the least positive integer $N$ such that $H$ contains
    \[ \ker(\widehat{O}^\times \to \modstar{O}{NO}). \]

The **level** of a {{KNOWL('shimcurve','Shimura curve')}} 
$X_H$ is the level of the corresponding open compact subgroup
$H$.
