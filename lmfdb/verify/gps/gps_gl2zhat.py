
from lmfdb.lmfdb_database import db
from sage.all import valuation
from ..verification import TableChecker, overall, slow

# Helper functions for this module

def bkm_const(p,d):
    # This is the B_0(p,d) constant
    if p == 2:
        return 8 + 2 * valuation(d,p)
    elif p == 3:
        return 5 + 2 * valuation(d,p)
    elif (p >= 5) and ((2*d) % (p-1) == 0):
        return 4 + 2 * valuation(d,p)
    else:
        return 2

def bkm_bounds(p, dims, mults):

    # The Brumer-Kramer-Martin bound for an abelian variety
    # that is isogenous to a product of abelian varieties
    # of GL(2)-type

    if p == 2:
        return sum([m * d * (bkm_const(p,d) + 1) for d,m in zip(dims, mults)])
    else:
        return sum([m * d * bkm_const(p,d) for d,m in zip(dims, mults)])

class gps_gl2zhat(TableChecker):
    table = db.gps_gl2zhat
    uniqueness_constraints = [["label"]]

    # We can't use the default check_label, since our labels come in two flavors
    @overall
    def check_label(self):
        """
        check that label is correct
        """
        bad_labels = self.check_string_concatenation("label", ["coarse_class", "coarse_num"], {"contains_negative_one":True})
        bad_labels += self.check_string_concatenation("label", ["level", "index", "genus", "coarse_level", "coarse_class_num", "coarse_num", "fine_num"],
                                                      constraint={"contains_negative_one":False},
                                                      sep=list("..-..."),
                                                      convert_to_base26={"coarse_class_num": -1})
        return bad_labels

    @overall
    def check_genus_equals_total_newform_dim(self):
        return self.check_array_dotproduct("dims", "mults", "genus", {"newforms": {"$exists": True}})

    @slow(ratio=1, constraint={'conductor':{'$exists':True}, 'contains_negative_one': True },
          projection=['conductor', 'newforms', 'mults', 'dims'])
    def check_conductor(self, rec):
        """
        Check conductor exponents satisfy the Brumer-Kramer-Martin bounds
        """
        for p, cond_exp in rec['conductor']:
            cond_exp_bound_this_p = bkm_bounds(p, rec['dims'], rec['mults'])
            if cond_exp > cond_exp_bound_this_p:
                return False

        return True
