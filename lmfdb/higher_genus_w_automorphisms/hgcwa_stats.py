# based on /lmfdb/elliptic_curves/ec_stats.py
# Authors: David Neill Asanza, Albert Ford, Ngi Nho, Jen Paulhus, Kevin Wang

from flask import url_for
from lmfdb import db
from lmfdb.backend import SQL

from lmfdb.utils import comma, display_knowl, StatsDisplay

def compute_total_refined_pp():
    # This is faster than db.hgcwa_passports.count_distinct('passport_label')
    return db._execute(SQL("SELECT SUM(num_refined_pp[1]) FROM hgcwa_complete")).fetchone()[0]

class HGCWAstats(StatsDisplay):
    """
    Class for creating and displaying statistics for higher genus curves with automorphisms
    """
    #TODO provide getter for subset of stats (e.g. for top matter)

    def __init__(self):
        self.genus_max = db.hgcwa_passports.max('genus')
        self.dim_max = db.hgcwa_passports.max('dim')
        self.g0_max = db.hgcwa_passports.max('g0')
        self.refined_passports_knowl = display_knowl(
            'curve.highergenus.aut.refinedpassport',
            title='refined passports')
        self.generating_vectors_knowl = display_knowl(
            'curve.highergenus.aut.generatingvector',
            title='generating vectors')
        self.dimension_knowl = display_knowl('curve.highergenus.aut.dimension', title = 'dimension'),
        self.distinct_generating_vectors = comma(db.hgcwa_passports.count())
        self.distinct_refined_passports = comma(compute_total_refined_pp())

        self.by_genus_data = init_by_genus_data()

    @property
    def short_summary(self):
        stats_url = url_for('.statistics')
        return (
            r'Currently the database contains all groups $G$ acting as '
            r'automorphisms of curves $X/\C$ of genus %s to %s such that $X/G$ '
            r'has genus 0, as well as genus 2 through 4 with quotient genus '
            r'greater than 0. There are %s distinct %s in the database. The '
            r'number of distinct %s is %s. Here are some '
            r'<a href="%s">further statistics</a>.' %
            (2, self.genus_max, self.distinct_refined_passports,
            self.refined_passports_knowl, self.generating_vectors_knowl,
            self.distinct_generating_vectors, stats_url)
        )

    @property
    def summary(self):
        return (
            r'Currently the database contains all groups $G$ acting as '
            r'automorphisms of curves $X$ from genus %s up to genus %s so that '
            r'the quotient space $X/G$ is the Riemann sphere ($X/G$ has genus 0). '
            r'There are %s distinct %s in the database. The number of distinct '
            r'%s is %s. ' %
            (2, self.genus_max, self.distinct_refined_passports,
            self.refined_passports_knowl, self.generating_vectors_knowl,
            self.distinct_generating_vectors)
        )

    baseurl_func = '.index'
    table = db.hgcwa_passports
    top_titles = {'dim': 'dimension'}
    short_display = {'dim': 'dimension'}
    stat_list = [{'cols': 'dim'}]


def init_by_genus_data():
    hgcwa = db.hgcwa_passports
    ##################################
    # Collect genus joint statistics #
    ##################################
    genus_detail = []
    for genus in range(2, hgcwa.max('genus') + 1):
        genus_data = db.hgcwa_complete.lookup(genus)
        genus_detail.append(
            {'genus_num': genus,
             'num_families': genus_data['num_families'],
             'num_refined_pp': genus_data['num_refined_pp'],
             'num_gen_vectors': genus_data['num_gen_vectors'],
             'num_unique_groups': genus_data['num_unique_groups'],
             'max_grp_order': hgcwa.max('group_order', {'genus':genus})})
    return genus_detail
