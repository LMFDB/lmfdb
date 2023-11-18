
from lmfdb.lmfdb_database import db
from .verification import TableChecker, overall

class gps_gl2zhat_fine(TableChecker):
    table = db.gps_gl2zhat_fine
    uniqueness_constraints = [["label"]]

    # We can't use the default check_label, since our labels come in two flavors
    #@overall
    #def check_label(self):
    #    bad_labels = self.check_string_concatenation("label", ["level", "index", "genus", "coarse_class", "coarse_num"], {"contains_negative_one":True})
    #    bad_labels += self.check_string_concatenation("label", ["coarse_level", "coarse_index", "genus", "coarse_class", "coarse_num", "level", "fine_num"], {"contains_negative_one":False}, sep=list("....-."))
    #    return bad_labels

    @overall
    def check_genus_equals_total_newform_dim(self):
        return self.check_array_dotproduct("dims", "mults", "genus", {"newforms": {"$exists": True}})
