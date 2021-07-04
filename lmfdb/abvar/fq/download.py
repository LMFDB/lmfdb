from lmfdb import db
from lmfdb.utils import Downloader
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