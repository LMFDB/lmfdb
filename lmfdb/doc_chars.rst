Characters
----------

==== =====================
 DG   Dirichlet group
 DC   Dirichlet character
 HG   Hecke group
 HC   Hecke character
==== =====================

============ ================= ==== ==== ==== ==== =====================
property      type              DG   HG   DC   HC   Example             
============ ================= ==== ==== ==== ==== =====================
title          str               X    X    X    X                            
credit         str               X    X    X    X                            
friends        [(label,tex)]     X    X    X    X
navi           [(label,tex),]    X    X    X    X
nf             tex                    X         X                     
nflabel        str                    X         X                      
nfpol          tex                    X         X                      
modulus        tex               X    X    X    X                      
modlabel       str               X    X    X    X                      
number         tex                         X    X                      
numlabel       str                         X    X                      
texname        tex                         X    X                         
symbol         tex                         X
previous       tex               X    X    X    X
prevmod        str               X    X    X    X
prevnum        str                         X    X
next           tex               X    X    X    X
nextmod        str               X    X    X    X
nextnum        str                         X    X
structure      tex               X    X                              
conductor      tex                         X    X                       
condlabel      str                         X    X                       
isprimitive    Yes/No                      X    X                       
inducing       tex                         X    X
indnum         str                         X    X
order          int               X    X    X    X                       
parity         Odd/Even                    X    X                       
isreal         Yes/No                      X    X                       
generators     tex               X    X    X    X                       
genvalues      tex                         X    X                       
logvalues      [ a/b, ]                    X    X                       
values         [ tex, ]                    X    X                       
galoisorbit  [(mod,num,tex)]               X    X                       
valuefield     tex                         X    X                       
vflabel        str                         X    X                       
vfpol          tex                         X    X                       
contents     [ rows ]            X    X
   row       (mod,num,tex,prp)   X    X
   prp       (prim,ord,vals)     X    X
============ ================= ==== ==== ==== ==== =====================


