title: Quaternion algebra
status: final-candidate
db: yes (in DB, consistent — reproduced verbatim)
waits_on: —
---
Let $F$ be a {{KNOWL('ring.field', 'field')}}. A **quaternion algebra** over $F$ is a central simple algebra of dimension 4 over $F$. 

A quaternion algebra
$B$ over a field $F$ of 
{{KNOWL('ring.characteristic','characteristic')}} not equal 
to 2 has elements $i,j \in B$ such that $\{1,i,j,ij\}$ is an 
$F$-basis for $B$, and such that there exists $a,b \in F^\times$ 
with $i^2 = a$, $j^2 = b$, and $ji = -ij$. In this case, we
write
    \[ B = \left(\frac{a,b}{F}\right).  \]
We set $k = ij$.

We say that a quaternion algebra $B$ over $F$ is **split** if $B$ is isomorphic to the matrix algebra $\operatorname{M}_2(F)$, and we say $B$ is **nonsplit** otherwise.

If $B$ is a quaternion algebra over $\Q$, we say that $B$ is **indefinite** if $B\otimes_\Q \R$ is a split quaternion algebra over $\R$, and we say $B$ is **definite** otherwise.
