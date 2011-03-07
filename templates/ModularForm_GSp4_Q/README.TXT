The Siege modular forms submodule provides currently information about
forms of seven groups. It is organized as follows:

Templates (which extend homepage.html)
=========

ModularForm_GSp4_Q_navigation.html

ModularForm_GSp4_Q_basic.html
ModularForm_GSp4_Q_dimensions.html
ModularForm_GSp4_Q_forms.html
ModularForm_GSp4_Q_gen_rel.html
ModularForm_GSp4_Q_specimen.html


Current groups (which extend the preceding templates, respectively)
==============

Gamma0_2_avail_forms.html
Gamma0_2_basic.html
Gamma0_2_gen_rel.html

Gamma0_3_psi_3_avail_forms.html
Gamma0_3_psi_3_basic.html
Gamma0_3_psi_3_gen_rel.html

Gamma0_4_psi_4_avail_forms.html
Gamma0_4_psi_4_basic.html
Gamma0_4_psi_4_gen_rel.html

Kp_avail_forms.html
Kp_basic.html
Kp_gen_rel.html

Sp4Z_2_basic.html
Sp4Z_2_gen_rel.html

Sp4Z_avail_forms.html
Sp4Z_basic.html
Sp4Z_gen_rel.html

Sp8Z_avail_forms.html
Sp8Z_basic.html
Sp8Z_gen_rel.html


Misc files
==========

None.html
README.TXT


--- 24.02.2011 Nils Skoruppa



Howto plug in new data
======================

Produce a directory New_Module on data.countnumber.de.  This directory
should contain minimally the following:

Contents.txt
available_eigenforms.p
eigenforms/
eigenvalues/

Contents.txt
------------
The file contains Copyright notices, descriptions etc.

eigenforms/
-----------
This directory contains Sage object files "naming_scheme.sobj", each
describing a Siegel modular form in the pickle format of the Siegel
modular forms package, i.e. in the format

(number field element a,
form as polynomial over Q[a] in the generators of the ring/module
[if available, "0" otherwise],
{[a,b,c]:coefficient at the binary form [a,b,c] as
polynomial in a}) 

eigenvalues/
------------
Contains Sage object files "naming_scheme-ev.sobj", each describing
the eigenvalues of a Siegel modular Hecke eigenform in the format

(number field element a, {prime p: eigenvalue of T(p) as polynomial in a})

available_eigenforms.p
----------------------
Contains information about the available forms in the above
directories.  The format is

{weight: {'Galois orbit name': dimension of this Galois orbit}}

Remark
------
The "naming_scheme" must consist of two parts, namely "weight" and a
"name", separated by an "_".


--- 05.03.2011 Nils Skoruppa