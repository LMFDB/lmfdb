

# belyi_galmaps
see: https://beta.lmfdb.org/api/belyi_galmaps/
column name     | type        | description
--------------------------------------------
id              | bigint      | (internal)
label           | text        | '6T7-4.2_4.2_3.3-a', '6T14-4.1.1_4.1.1_3.3-a', '8T24-6.2_2.2.1.1.1.1_4.4-a', '9T16-6.3_4.4.1_2.2.2.1.1.TODO: resort the cycle type, e.g.: '6T7-4.2_3.3_4.2-a', '6T14-4.1.1_3.3_4.1.1-a', '8T24-6.2_2.2.1.1.1.1_4.4-a', '9T16-6.3_2.2.2.1.1.1_4.4.1-a' (Sam)
deg             | smallint    | the degree of the belyi map
group           | text        | e.g. '4T1'
group_num       | smallint    | the 't' number in the 'dTt' notation
geomtype        | text        | \in ['E', 'H', 'S'] ~ ['Euclidean', 'hyperbolic', 'spherical']
map             | text        | text of the map (deprecated) -> moved to models
abc             | smallint[]  | e.g., [4, 4, 2]
base_field      | numeric[]   | the (polredabs) coefficients of the field of definition
base_field_label| text        | the label of the field of definition TODO: fill this column
moduli_field    | numeric[]   | the (polredabs) coefficients of the field of moduli
moduli_field_label| text      | the label of the field of moduli TODO: fill this column
embeddings      | jsonb       | complex embeddings of the base_field TODO: sort
triples         | jsonb       | generators as elements of the permutation group per embedding.
triples_cyc     | jsonb       | generators in cyclic notation per embedding TODO: text -> integers, eg '(1, 4, 3, 6)(2, 5, 8, 7)' -> [[1,4,3,6], [2, 5, 8, 7]]
g               | smallint    | genus
curve           | text        | equation of the curve (deprecated) -> moved to models
specializations | jsonb       | a map t -> data about the specialization
a_s             | smallint    | the smallest element of abc
b_s             | smallint    | the second smallest element of abc
c_s             | smallint    | the largest element of abc
orbit_size      | smallint    |
pass_size       | smallint    |
aut_group       | jsonb       | containing the generators in one line notation e.g.  [[7, 4, 5, 2, 3, 8, 1, 6], [8, 1, 2, 7, 4, 5, 6, 3]] TODO: move to the passport?
plabel          | text        | passport label, e.g., '4T5-4_3.1_2.1.1'
lambdas         | jsonb       | conjugacy type of each triple as a partition
curve_label     | text        | the label of the curve on LMFDB
friends         | text[]      | list of urls for other friends on LMFDB
old_label       | text        | deprecated
old_plabel      | text        | deprecated
models          | jsonb       | a list of dictionaries with models TODO: new

# belyi_passports
see: https://beta.lmfdb.org/api/belyi_passports/
column name     | type        | description
--------------------------------------------
id              | bigint      | (internal)
geomtype        | text        | \in ['E', 'H', 'S'] ~ ['Euclidean', 'hyperbolic', 'spherical']
abc             | smallint[]  | e.g., [4, 4, 2]
a_s             | smallint    | the smallest element of abc
b_s             | smallint    | the second smallest element of abc
c_s             | smallint    | the largest element of abc
group           | text        | the group in 'nTt' notation, e.g. '4T1'
g               | smallint    | genus
pass_size       | smallint    |
maxdegbf        | smallint    | ?
lambdas         | jsonb       |
plabel          | text        |
num_orbits      | smallint    |
deg             | smallint    | the degree of the Belyi map
old_plabel      | text        | deprecated


