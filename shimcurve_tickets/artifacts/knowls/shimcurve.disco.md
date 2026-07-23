title: Discriminant of a quaternion order
status: final-candidate
db: yes (in DB, consistent — reproduced verbatim)
waits_on: —
---
Let $B$ be a {{KNOWL('shimcurve.quaternion_algebra','quaternion algebra')}} over $\Q$, and let $O\subset B$ be an 
{{KNOWL('shimcurve.order','order')}}. Let $x_1,x_2,x_3,x_4 \in O$
be a $\Z$-basis of $O$. The **discriminant** of $O$ is the 
integer
    \[ \operatorname{disc}(O) 
        \colonequals \left|\det(\operatorname{trd}(x_ix_j))_{i,j}\right|. \]
where $\operatorname{trd} : B \to \Q$ is the reduced trace. 

The **reduced discriminant** of $O$ is the positive integer
$\operatorname{discrd}(O)$ such that
    \[ \operatorname{discrd}(O)^2 = \operatorname{disc}(O). \]
