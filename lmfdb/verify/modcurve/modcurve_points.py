from sage.all import lazy_attribute
from lmfdb.lmfdb_database import db
from ..verification import TableChecker, slow

class modcurve_points(TableChecker):
    table = db.modcurve_points

    # The following column isn't the label column, but it's the
    # closest one we have to it. This gets used for reporting
    # on failed tests.
    label_col = 'coordinates'

    @lazy_attribute
    def relevant_cusp_orbits(self):
        # Get all curve_labels needed (distinct values only)
        curve_labels = list({x for x in db.modcurve_points.search({'degree': {"$lte": 6}, 'cusp': True}, projection="curve_label")})

        # Batch fetch from gps_gl2zhat
        records = db.gps_gl2zhat.search({'curve_label': {'$in': curve_labels}}, projection=["curve_label", "cusp_orbits"])

        # Build the mapping
        return {rec["curve_label"]: rec["cusp_orbits"] for rec in records}


    @slow(ratio=1, projection=['cusp', 'degree', 'cardinality', 'curve_label'],
          constraint={'cusp': True, 'degree':{"$lte":6}})
    def check_cusp_data_matches_orbits(self, rec):
        """
        Verify that a (degree, cardinality) pair from modcurve_points
        is listed in the cusp_orbits for the corresponding curve.
        Skip the check if degree or cardinality is missing.
        """
        degree = rec.get('degree')
        cardinality = rec.get('cardinality')

        if degree is None or cardinality is None:
            return True  # skip the check, treat as passed

        cusp_orbits = self.relevant_cusp_orbits.get(rec['curve_label'])
        if cusp_orbits is None:
            # if we can't find cusp orbit data then we can't proceed, so effectively skip this case
            return True

        if [degree, cardinality] not in cusp_orbits:
            return False
        return True

