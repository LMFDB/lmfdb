from lmfdb import db
from lmfdb.utils import Downloader
from flask import abort
from lmfdb.backend.encoding import Json

class AbvarFq_download(Downloader):
    table = db.av_fq_isog
    title = 'Abelian variety isogeny classes'

    def download_all(self, label, lang='text'):
        data = db.av_fq_isog.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s"%label)
        return self._wrap(Json.dumps(data),
                          label,
                          lang=lang,
                          title='Stored data for abelian variety isogeny class %s,'%(label))

    def download_curves(self, label, lang='text'):
        data = db.av_fq_isog.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s"%label)
        if 'curves' not in data or ('curves' in data and not data['curves']):
            return abort(404, "No curves for abelian variety isogeny class %s"%label)
        return self._wrap('\n'.join(data['curves']),
                          label + '.curves',
                          lang=lang,
                          title='Curves in abelian variety isogeny class %s,'%(label))
