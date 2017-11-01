# based on /lmfdb/elliptic_curves/ec_stats.py

import re
from lmfdb.base import getDBConnection
from lmfdb.utils import make_logger

logger = make_logger("hgcwa")

the_HGCWAstats = None

def db_hgcwa_stats():
    return getDBConnection().curve_automorphisms.passports.stats

def get_stats_object():
    global the_HGCWAstats
    if the_HGCWAstats is None:
        the_HGCWAstats = HGCWAstats()
    return the_HGCWAstats

def max_group_order(counts):
    orders = []
    for count in counts:
        group = count[0]
        order = int(re.search(r'\[(\d+)', group).group(1))
        orders.append(order)
    return max(orders)

class HGCWAstats(object):
    """
    Class for creating and displaying statistics for higher genus curves with automorphisms
    """

    def __init__(self):
        logger.debug("Constructing an instance of HGCWAstats")
        self.hgcwa_stats = db_hgcwa_stats()
        self._counts = {}
        self._stats = self.compute_stats()

    def stats(self):
        return self._stats

    def compute_stats(self):
        logger.debug("Computing elliptic curve stats...")

        db = self.hgcwa_stats
        stats = {}

        # Populate simple data
        stats['genus_summary'] = db.find_one({'_id':'genus'})
        stats['dim_summary'] = db.find_one({'_id':'dim'})

        # An iterable list of distinct curve genera
        genus_list = [ count[0] for count in stats['genus_summary']['counts'] ]
        genus_list.sort()

        # Get unique joint genus stats
        stats['genus'] = []

        for genus in genus_list:
            genus_stats = {}
            genus_stats['genus_num'] = genus
            genus_str = str(genus)

            # Get group data
            groups = db.find_one({'_id':'bygenus/' + genus_str + '/group'})
            group_count = len(groups['counts'])
            group_max_order = max_group_order(groups['counts'])
            genus_stats['groups'] = [group_count, group_max_order]

            # Get family data
            families = db.find_one({'_id':'bygenus/' + genus_str + '/label'})
            family_count = len(families['counts'])
            genus_stats['families'] = family_count

            # Get refined passport data
            rps = db.find_one({'_id':'bygenus/' + genus_str + '/passport_label'})
            rp_count = len(rps['counts'])
            genus_stats['refined_passports'] = rp_count

            # TODO May be redundant, see genus data
            # Get generating vector data
            gvs = db.find_one({'_id':'bygenus/' + genus_str + '/total_label'})
            gv_count = len(gvs['counts'])
            genus_stats['gen_vectors'] = gv_count

            # Keep genus data sorted
            stats['genus'].append(genus_stats)

        return stats
