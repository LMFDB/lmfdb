"""
All the funtions needed in `import_ecnf_data.py` that don't need acces to the ec database.
"""
# Label of an ideal I in a quadratic field: string formed from the
# Norm and HNF of the ideal
import re
from sage.all import cm_j_invariants_and_orders, ZZ, QQ
from lmfdb.ecnf.WebEllipticCurve import ideal_HNF

def NFelt(a):
    r""" Returns an NFelt string encoding the element a (in a number field
    K).  This consists of d strings representing the rational
    coefficients of a (with respect to the power basis), separated by
    commas, with no spaces.

    For example the element (3+4*w)/2 in Q(w) gives '3/2,2'.
    """
    return ",".join([str(c) for c in list(a)])

def QorZ_list(a):
    r"""
    Return the list representation of the rational number.
    """
    return [int(a.numerator()), int(a.denominator())]


def K_list(a):
    r"""
    Return the list representation of the number field element.
    """
    # return [QorZ_list(c) for c in list(a)]  # old: [num,den]
    return [str(c) for c in list(a)]         # new: "num/den"


def NFelt_list(a):
    r"""
    Return the list representation of the NFelt string.
    """
    return [QorZ_list(QQ(c)) for c in a.split(",")]

def point_string(P):
    r"""Return a string representation of a point on an elliptic
    curve. This is a single string representing a list of 3 lists,
    each representing one coordinate as an NFelt string, with no
    spaces.

    For example, over a field of degree 2, [0:0:1] gives
    '[0,0],[0,0],[1,0]'.
    """
    s = "[" + ",".join(["".join(["[",NFelt(c),"]"]) for c in list(P)]) + "]"
    return s

def point_string_to_list(s):
    r"""Return a list representation of a point string
    """
    return s[1:-1].split(":")


def point_list(P):
    r"""Return a list representation of a point on an elliptic curve
    """
    return [K_list(c) for c in list(P)]

#@cached_function
def get_cm_list(K):
    return cm_j_invariants_and_orders(K)

def get_cm(j):
    r"""
    Returns the CM discriminant for this j-invariant, or 0
    """
    if not j.is_integral():
        return 0
    for d, f, j1 in get_cm_list(j.parent()):
        if j == j1:
            return int(d * f * f)
    return 0

whitespace = re.compile(r'\s+')


def split(line):
    return whitespace.split(line.strip())

def numerify_iso_label(lab):
    from sage.databases.cremona import class_to_int
    if 'CM' in lab:
        return -1 - class_to_int(lab[2:])
    else:
        return class_to_int(lab.lower())


def ideal_label(I):
    r"""
    Returns the HNF-based label of an ideal I in a quadratic field
    with integral basis [1,w].  This is the string 'N.c.d' where
    [a,c,d] is the HNF form of I and N=a*d=Norm(I).
    """
    a, c, d = ideal_HNF(I)
    return "%s.%s.%s" % (a * d, c, d)

# Reconstruct an ideal in a quadratic field from its label.


def ideal_from_label(K, lab):
    r"""Returns the ideal with label lab in the quadratic field K.
    """
    N, c, d = [ZZ(c) for c in lab.split(".")]
    a = N // d
    return K.ideal(a, K([c, d]))





def isoclass(line):
    r""" Parses one line from an isoclass file.  Returns the label and a dict
    containing fields with keys .

    Input line fields (5); the first 4 are the standard labels and the
    5th the isogeny matrix as a list of lists of ints.

    field_label conductor_label iso_label number isogeny_matrix

    Sample input line:

    2.0.4.1 65.18.1 a 1 [[1,6,3,18,9,2],[6,1,2,3,6,3],[3,2,1,6,3,6],[18,3,6,1,2,9],[9,6,3,2,1,18],[2,3,6,9,18,1]]
    """
    # Parse the line and form the full label:
    data = split(line)
    if len(data) < 5:
        print "isoclass line %s does not have 5 fields (excluding gens), skipping" % line
    field_label = data[0]       # string
    conductor_label = data[1]   # string
    iso_label = data[2]         # string
    number = int(data[3])       # int
    short_label = "%s-%s%s" % (conductor_label, iso_label, str(number))
    label = "%s-%s" % (field_label, short_label)

    mat = data[4]
    mat = [[int(a) for a in r.split(",")] for r in mat[2:-2].split("],[")]
    isogeny_degrees = dict([[n+1,sorted(list(set(row)))] for n,row in enumerate(mat)])

    edata = {'label': data[:4], 'isogeny_matrix': mat, 'isogeny_degrees': isogeny_degrees}
    return label, edata




def make_curves_line(ec):
    r""" for ec a curve object from the database, create a line of text to
    match the corresponding raw input line from a curves file.

    Output line fields (13):

    field_label conductor_label iso_label number conductor_ideal conductor_norm a1 a2 a3 a4 a6 cm base_change

    Sample output line:

    2.0.4.1 65.18.1 a 1 [65,65,-4*w-7] 65 1,1 1,1 0,1 -1,1 -1,0 0 0
    """
    cond_lab = ec['conductor_label']
    output_fields = [ec['field_label'],
                     cond_lab,
                     ec['iso_label'],
                     str(ec['number']),
                     ec['conductor_ideal'],
                     str(ec['conductor_norm'])
                    ]  + ec['ainvs'].split(";") + [str(ec['cm']), '?' if ec['base_change']=='?' else str(int(len(ec['base_change']) > 0))]
    return " ".join(output_fields)



def make_curve_data_line(ec):
    r""" for ec a curve object from the database, create a line of text to
    match the corresponding raw input line from a curve_data file.

    Output line fields (9+n where n is the 8th); all but the first 4
    are optional and if not known should contain"?" except that the 8th
    should contain 0.

    field_label conductor_label iso_label number rank rank_bounds analytic_rank ngens gen_1 ... gen_n sha_an

    Sample output line:

    2.0.4.1 2053.1809.1 a 1 2 [2,2] ? 2 [[0,0],[-1,0],[1,0]] [[2,0],[2,0],[1,0]] ?
    """
    rk = '?'
    if 'rank' in ec:
        rk = str(ec['rank'])
    rk_bds = '?'
    if 'rank_bounds' in ec:
        rk_bds = str(ec['rank_bounds']).replace(" ", "")
    an_rk = '?'
    if 'analytic_rank' in ec:
        an_rk = str(ec['analytic_rank'])
    gens = ec.get('gens',[])
    ngens = str(len(gens))
    sha = '?'
    if 'sha_an' in ec:
        sha = str(int(ec['sha_an']))

    cond_lab = ec['conductor_label']
    output_fields = [ec['field_label'],
                     cond_lab,
                     ec['iso_label'],
                     str(ec['number']),
                     rk, rk_bds, an_rk,
                     ngens] + gens + [sha]
    return " ".join(output_fields)


