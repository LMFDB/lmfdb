from flask import url_for
from lmfdb import db
from lmfdb.utils import comma, StatsDisplay, display_knowl, proportioners, totaler
from lmfdb.logger import make_logger

logger = make_logger("genus")

class Genus_stats(StatsDisplay):
    def __init__(self):
        self.ngenera = comma(db.lat_genera.count())
        self.max_cn = db.lat_genera.max("class_number")
        self.max_rank = db.lat_genera.max("rank")
        self.max_det = db.lat_genera.max("det")
        self.kintegral = display_knowl('lattice.definition', 'integral lattices')
        self.ksignature = display_knowl('lattice.signature', 'signatures')
        #self.kcatalogue = display_knowl('lattice.catalogue_of_lattices', 'Catalogue of Lattices')
        self.kcn = display_knowl('lattice.class_number', 'class number')
        self.kdim = display_knowl('lattice.dimension', 'rank')
        self.kdet = display_knowl('lattice.determinant', 'determinant')
        self.kpri = display_knowl('lattice.primitive', 'primitive')

    @property
    def short_summary(self):
        return 'The database currently contains {} genera of {} of varying {}. The largest {} is {}, the largest {} is {}, and the largest {} is {}. Here are some <a href="{}">further statistics</a>.'.format(
            self.ngenera,
            self.kintegral,
            self.ksignature,
            self.kcn,
            self.max_cn,
            self.kdim,
            self.max_rank,
            self.kdet,
            comma(self.max_det),
            url_for(".statistics"))

    table = db.lat_genera
    baseurl_func = ".genus_render_webpage"
    buckets = {"rank":["1","2","3","4","5","6","7","8","9","10","11","12"],
               "det":["1","2-10","11-100","101-1000"],
               "class_number":["1","2","3","4-7","8-15","16-31","32-63"],
               }
    knowls = {'rank': 'lattice.dimension',
              'det': 'lattice.determinant',
              'class_number': 'lattice.class_number',
              }
    short_display = {'rank': 'rank',
                     'det': 'determinant',
                     }
    stat_list = [
        {"cols": ["det", "rank"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
        {"cols": ["class_number", "rank"],
         "proportioner": proportioners.per_col_total,
         "totaler": totaler()},
    ]
