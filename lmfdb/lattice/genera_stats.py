from flask import url_for
from lmfdb import db
from lmfdb.utils import comma, StatsDisplay, display_knowl, proportioners, totaler
from lmfdb.logger import make_logger

logger = make_logger("genus")

class Genus_stats(StatsDisplay):
    def __init__(self):
        self.ngenera = comma(db.lat_genera.count())
        # self.max_cn = db.lat_lattices.max("class_number")
        self.max_rank = db.lat_genera.max("rank")
        self.max_det = db.lat_genera.max("det")
        # self.kposdef = display_knowl('lattice.postive_definite', 'positive definite')
        self.kintegral = display_knowl('lattice.definition', 'integral lattices')
        self.kcatalogue = display_knowl('lattice.catalogue_of_lattices', 'Catalogue of Lattices')
        # self.kcn = display_knowl('lattice.class_number', 'class number')
        self.kdim = display_knowl('lattice.dimension', 'dimension')
        self.kdet = display_knowl('lattice.determinant', 'determinant')
        self.kpri = display_knowl('lattice.primitive', 'primitive')

    @property
    def short_summary(self):
        return 'The database currently contains {} genera of {}. The largest {} is {}, and the largest {} is {}. Here are some <a href="{}">further statistics</a>.'.format(
            self.ngenera,
            self.kintegral,
            self.kdim,
            self.max_rank,
            self.kdet,
            comma(self.max_det),
            url_for(".statistics"))

    table = db.lat_genera
    baseurl_func = ".genus_render_webpage"
    buckets = {"rank":["1","2","3","4","5","6","7","8-15","16-31"],
               "det":["1","2-10","11-100","101-1000","1001-10000","10001-100000","100001-1000000"],
               # "minimum":["1","2","3","4-7","8-15","16-31","32-63","64-127","128-255"],
               # "class_number":["1","2","3","4-7","8-15","16-31","32-63"],
               # "aut":["2","4","8","12","16","24","32","33-128", "129-512","513-2048","2049-16384","16385-262144","262145-8388608","8388609-191102976"]
               }
    knowls = {'rank': 'lattice.dimension',
              'det': 'lattice.determinant',
              #'minimum': 'lattice.minimal_vector',
              #'class_number': 'lattice.class_number',
              #'aut': 'lattice.group_order'
              }
    short_display = {'rank': 'rank',
                     'det': 'determinant',
                     #'minimum': 'minimal length',
                     #'aut': 'automorphism order'
                     }
    top_titles = {#'minimum': 'minimal vector length',
                  #'aut': 'automorphism group order'
        }
    stat_list = [
        {"cols": ["det", "rank"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        #{"cols": ["minimum", "dim"],
        # "proportioner": proportioners.per_col_total,
        # "totaler": totaler()},
        #{"cols": ["class_number", "dim"],
        # "proportioner": proportioners.per_col_total,
        # "totaler": totaler()},
        #{"cols": ["aut", "dim"],
        # "proportioner": proportioners.per_col_total,
        # "totaler": totaler()},
    ]
