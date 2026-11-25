from flask import abort
from psycodict.encoding import Json

from lmfdb.utils import Downloader
from .web_k3fq import isog_table, WebK3Fq


class K3Fq_download(Downloader):
    table = isog_table
    title = "Motives of K3 type over finite fields"
    short_name = "class"
    var_name = "classes"
    filebase = "k3_fq_isog"

    def download_all(self, label, lang="text"):
        data = isog_table.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s" % label)
        return self._wrap(Json.dumps(data),
                          label,
                          lang=lang,
                          title="Stored data for the motive of K3 type %s," % (label))

    def postprocess(self, rec, info, query):
        return WebK3Fq(rec)
