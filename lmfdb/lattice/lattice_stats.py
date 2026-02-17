from flask import url_for
from lmfdb import db
from lmfdb.utils import comma, StatsDisplay, display_knowl, proportioners, totaler
from lmfdb.logger import make_logger

logger = make_logger("lattice")

class Lattice_stats(StatsDisplay):
    def __init__(self):
        self.nlats = comma(db.lat_lattices_new.count())
        self.max_cn = db.lat_lattices_new.max("class_number")
        self.max_rank = db.lat_lattices_new.max("rank")
        self.max_det = db.lat_lattices_new.max("det")
        self.kintegral = display_knowl('lattice.definition', 'integral lattices')
        self.ksignature = display_knowl('lattice.signature', 'signatures')
        #self.kcatalogue = display_knowl('lattice.catalogue_of_lattices', 'Catalogue of Lattices')
        self.kcn = display_knowl('lattice.class_number', 'class number')
        self.kdim = display_knowl('lattice.dimension', 'rank')
        self.kdet = display_knowl('lattice.determinant', 'determinant')
        self.kpri = display_knowl('lattice.primitive', 'primitive')

    @property
    def short_summary(self):
        return 'The database currently contains {} {} of varying {}. The largest {} is {}, the largest {} is {}, and the largest {} is {}. Here are some <a href="{}">further statistics</a>.'.format(
            self.nlats,
            self.kintegral,
            self.ksignature,
            #self.kcatalogue,
            self.kcn,
            self.max_cn,
            self.kdim,
            self.max_rank,
            self.kdet,
            comma(self.max_det),
            url_for(".statistics"),
        )

    table = db.lat_lattices_new
    baseurl_func = ".index"
    buckets = {"rank":["1","2","3","4","5","6","7","8","9","10","11","12"],
               "det":["1","2-10","11-100","101-1000"],
               "minimum":["1","2","3","4-7","8-15","16-31","32-63","64-127","128-255"],
               "class_number":["1","2","3","4-7","8-15","16-31","32-63"],
               "aut_size":["2","4","8","12","16","24","32","33-128", "129-512","513-2048","2049-16384","16385-262144","262145-8388608","8388609-191102976"]}
    knowls = {'rank': 'lattice.dimension',
              'det': 'lattice.determinant',
              'minimum': 'lattice.minimal_vector',
              'class_number': 'lattice.class_number',
              'aut_size': 'lattice.group_order'}
    short_display = {'dim': 'dimension',
                     'det': 'determinant',
                     'minimum': 'minimal length',
                     'aut_size': 'automorphism order'}
    top_titles = {'minimum': 'minimal vector length',
                  'aut_size': 'automorphism group order'}
    stat_list = [
        {"cols": ["det", "rank"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["minimum", "rank"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["class_number", "rank"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["aut_size", "rank"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
    ]
