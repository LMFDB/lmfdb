#!/usr/bin/env -S sage -python

"""
This script is used to perform additional verification on uploads before review by a human editor.  Simple verifications are performed when an LMFDB user uploads data, but additional verification (anything requiring a nontrivial amount of computation for example) are performed by this script.  It is intended for use by a cron job, and is called with no arguments.
"""

import os
import sys
import tempfile
from lmfdb.utils.datetime_utils import utc_now_naive
here = os.path.dirname(os.path.abspath(__file__))
upone, _ = os.path.split(here)
uptwo, _ = os.path.split(upone)
sys.path.append(uptwo)
from lmfdb import db
from lmfdb.users.main import Reviewer


def verify_all():
    raise NotImplementedError("This script has been disabled until the verify methods in modular curves are complete")
    reviewer = Reviewer()
    # TODO: it would be better to isolate each verification in its own process to insulate against timeouts
    with tempfile.NamedTemporaryFile("w", delete=False) as F:
        columns = ["id", "status", "verified", "updated", "comment"]
        types = ["bigint", "smallint", "timestamp without time zone", "timestamp without time zone", "text"]
        _ = F.write("|".join(columns) + "\n" + "|".join(types) + "\n\n")
        for rec in db.data_uploads.search({"status":0}, ["data", "id", "section"]):
            try:
                section = reviewer.section_lookup[rec["section"]]
                section.verify(rec["data"])
            except Exception as err:
                status = -1
                comment = str(err).replace("\n", "    ")
            else:
                status = 1
                comment = ""
            timestamp = utc_now_naive().isoformat()
            _ = F.write(f"{rec['id']}|{status}|{timestamp}|{timestamp}|{comment}\n")
        F.close()
        db.data_uploads.update_from_file(F.name, "id")
        db.data_uploads.cleanup_from_reload()
        os.unlink(F.name)

verify_all()
