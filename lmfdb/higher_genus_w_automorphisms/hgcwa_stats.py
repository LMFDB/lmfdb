# based on /lmfdb/elliptic_curves/ec_stats.py

import re
from lmfdb.db_backend import db
from sage.all import UniqueRepresentation, cached_method
from lmfdb.utils import make_logger

logger = make_logger("hgcwa")

def oldstat(name):
    return db.hgcwa_passports.stats.get_oldstat(name)

def max_group_order(counts):
    orders = []
    for count in counts:
        group = count[0]
        order = int(re.search(r'\[(\d+)', group).group(1))
        orders.append(order)
    return max(orders)

class HGCWAstats(UniqueRepresentation):
    """
    Class for creating and displaying statistics for higher genus curves with automorphisms
    """
    #TODO provide getter for subset of stats (e.g. for top matter)
    @cached_method
    def stats(self):
        logger.debug("Computing elliptic curve stats...")
        stats = {}

        # Populate simple data
        stats['genus'] = oldstat('genus')
        stats['dim'] = oldstat('dim')
        stats['refined_passports'] = oldstat('passport_label')
        stats['generating_vectors'] = oldstat('total_label')

        ##################################
        # Collect genus joint statistics #
        ##################################

        # An iterable list of distinct curve genera
        genus_list = [ count[0] for count in stats['genus']['counts'] ]
        genus_list.sort()

        genus_family_counts = oldstat('bygenus/label')
        genus_rp_counts = oldstat('bygenus/passport_label')
        genus_gv_counts = oldstat('bygenus/total_label')

        # Get unique joint genus stats
        stats['genus_detail'] = []

        for genus in genus_list:
            genus_stats = {}
            genus_stats['genus_num'] = genus
            genus_str = str(genus)

            # Get group data
            groups = oldstat('bygenus/' + genus_str + '/group')
            group_count = len(groups['counts'])
            group_max_order = max_group_order(groups['counts'])
            genus_stats['groups'] = [group_count, group_max_order]

            # Get family, refined passport and generating vector data
            genus_stats['families'] = genus_family_counts['distinct'][genus_str]
            genus_stats['refined_passports'] = genus_rp_counts['distinct'][genus_str]
            genus_stats['gen_vectors'] = genus_gv_counts['distinct'][genus_str]

            # Keep genus data sorted
            stats['genus_detail'].append(genus_stats)

        ######################################
        # Collect dimension joint statistics #
        ######################################

        # An iterable list of distinct curve genera
        dim_list = [ count[0] for count in stats['dim']['counts'] ]
        dim_max = max(dim_list)

        dim_gv_counts = oldstat('bydim/total_label')

        # Get unique joint genus stats
        stats['dim_detail'] = []

        for dim in range(0, dim_max+1):
            dim_stats = {}
            dim_stats['dim_num'] = dim
            dim_str = str(dim)

            try:
                dim_stats['gen_vectors'] = dim_gv_counts['distinct'][dim_str]
            except KeyError:
                dim_stats['gen_vectors'] = 0

            # Keep dimension data sorted
            stats['dim_detail'].append(dim_stats)

        return stats
