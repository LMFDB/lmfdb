
from sage.all import ProjectiveSpace, PolynomialRing, QQ

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

    @slow(projection=['domain_label', 'codomain_label', 'coordinates', 'domain_model_type', 'codomain_model_type'])
    def check_rat_pts_map_to_rat_pts(self, rec):
        """
        given a rational point on a modular curve, and a map from this modular curve
        to another one, check that the image is a rational point on the latter curve
        """

        # First look up ratpts on the domain

        for point in db.modcurve_points.search({'curve_label':rec['domain_label'],
                                                'coordinates':{'$exists':True}}):
            try:
                relevant_pts = point['coordinates'][rec['domain_model_type']]  # these are the pts that can be hit with the map
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
                codomain_info = db.modcurve_models.lookup({'modcurve':rec['codomain_label'],
                                                       'model_type':rec['codomain_model_type']},
                                                       projection=['equation', 'number_variables'])
                codomain_info = list(codomain_info)
                assert len(codomain_info) == 1  # multiple entries is bad
                codomain_info = codomain_info[0]
                Pol = PolynomialRing(QQ, codomain_info['number_variables'], names=VARORDER[:codomain_info['number_variables']])
                for f_str in codomain_info['equation']:
                    assert Pol(f_str)(pt_on_codomain_as_list) == 0, "point not on codomain"
                
                ### TEST 3: check this pt is accounted for in modcurve_points

                # 3a. first get the points on the codomain
                points_on_codomain_with_this_j = db.modcurve_points.lookup({'curve_label':rec['codomain_label'],
                                                'jinv':jinv_this_pt})
                points_on_codomain_with_this_j = list(points_on_codomain_with_this_j)
                assert len(points_on_codomain_with_this_j) == 1

                # 3b. now check the point is among them
                pts_on_codomain_as_str = points_on_codomain_with_this_j['coordinates'][rec['codomain_model_type']]  # a list of strings
                P = ProjectiveSpace(QQ, codomain_info['number_variables'] - 1, names=VARORDER[:codomain_info['number_variables']])
                assert P(pt_on_codomain_as_list) in [P(pt_str.split(':')) for pt_str in pts_on_codomain_as_str], "missing point"
        
        return True

