
from sage.all import ProjectiveSpace, PolynomialRing, QQ, lazy_attribute
from collections import defaultdict

from lmfdb.lmfdb_database import db
from lmfdb.modular_curves.upload import VARORDER
from ..verification import TableChecker, slow


def apply_map_to_pt(a_map, a_pt):
    how_many_vars = a_pt.count(':') + 1
    my_vars = VARORDER[:how_many_vars]
    P = ProjectiveSpace(QQ, how_many_vars - 1, names=my_vars)
    my_pt = P(a_pt.split(':'))
    Pol = PolynomialRing(QQ, how_many_vars, names=my_vars)
    output = []
    my_pt_tuple = tuple(my_pt)
    for a_pol in a_map:
        output.append(Pol(a_pol)(my_pt_tuple))
    return output


class modcurve_modelmaps(TableChecker):
    table = db.modcurve_modelmaps
    label_col = 'domain_label'

    @lazy_attribute
    def modcurve_points(self):
        ans = defaultdict(list)
        for rec in db.modcurve_points.search({'degree': 1}, ["curve_label", "coordinates", "jinv"]):
            ans[rec["curve_label"]].append(rec)
        return ans

    @lazy_attribute
    def modcurve_models(self):
        ans = {}
        for rec in db.modcurve_models.search({}, ["modcurve", "model_type", "equation", "number_variables"]):
            ans[rec["modcurve"], rec["model_type"]] = (rec["equation"], rec["number_variables"])
        return ans

    @slow(ratio=1, projection=['domain_label', 'codomain_label', 'coordinates', 'domain_model_type', 'codomain_model_type'],
          constraint={'domain_model_type':{"$ne":1}, 'codomain_model_type':{"$ne":1}})
    def check_rat_pts_map_to_rat_pts(self, rec):
        """
        given a rational point on a modular curve, and a map from this modular curve
        to another one, check that the image is a rational point on the latter curve
        """

        # First look up ratpts on the domain
        for point in self.modcurve_points[rec["domain_label"]]:
            if not point.get("coordinates"):
                continue
            try:
                relevant_pts = point['coordinates'][str(rec['domain_model_type'])]  # these are the pts that can be hit with the map
                print(f"Found point on {rec['domain_label']}")
            except KeyError:
                # means there are no points on the model required by the map
                continue
            jinv_this_pt = point['jinv']  # needed for the third test below
            for rel_pt in relevant_pts:
                pt_on_codomain_as_list = apply_map_to_pt(rec['coordinates'], rel_pt)

                # TEST 1: check this pt is rational
                if not all([t in QQ for t in pt_on_codomain_as_list]):
                    return False

                # TEST 2: check this is actually a point on the codomain
                equation, number_variables = self.modcurve_models[rec["codomain_label"], rec["codomain_model_type"]]
                Pol = PolynomialRing(QQ, number_variables, names=VARORDER[:number_variables])
                for f_str in equation:
                    assert Pol(f_str)(pt_on_codomain_as_list) == 0, "point not on codomain"

                ### TEST 3: check this pt is accounted for in modcurve_points

                # 3a. first get the points on the codomain
                points_on_codomain_with_this_j = [rec for rec in self.modcurve_points[rec["codomain_label"]] if rec["jinv"] == jinv_this_pt]
                assert len(points_on_codomain_with_this_j) == 1

                # 3b. now check the point is among them
                if str(rec['codomain_model_type']) in points_on_codomain_with_this_j[0]['coordinates']:
                    pts_on_codomain_as_str = points_on_codomain_with_this_j[0]['coordinates'][str(rec['codomain_model_type'])]
                else:
                    # Means we don't have coordinates on the model we're dealing with, so can't do anything
                    continue
                P = ProjectiveSpace(QQ, number_variables - 1, names=VARORDER[:number_variables])
                assert P(pt_on_codomain_as_list) in [P(pt_str.split(':')) for pt_str in pts_on_codomain_as_str], "missing point"
        return True

