#!/usr/bin/env -S sage -python

"""
This script is used to convert perform additional verification on uploads before review by a human editor.  Simple verifications are performed when an LMFDB user uploads data, but additional verification (anything requiring a nontrivial amount of computation for example) are performed by this script.  It is intended for use by a cron job, and is called with no arguments.
"""

import os
import sys
import tempfile
from collections import defaultdict
from lmfdb.utils.datetime_utils import utc_now_naive
here = os.path.dirname(os.path.abspath(__file__))
data_folder = os.path.join(here, "data")
upone, _ = os.path.split(here)
uptwo, _ = os.path.split(upone)
sys.path.append(uptwo)
from lmfdb import db
from psycodict.encoding import copy_dumps
from lmfdb.users.main import Reviewer


def process_all():
    os.makedirs("data", exist_ok=True)
    by_table = defaultdict(list)
    cols = {}
    status_update = defaultdict(dict)
    sections = set()
    reviewer = Reviewer()
    # TODO: it might be better to isolate each verification in its own process to insulate against timeouts
    # This would prevent sharing some computations, like the poset of modular curves, between different uploads
    with tempfile.NamedTemporaryFile("w", delete=False) as F:
        columns = ["id", "status", "processed", "updated", "comment"]
        types = ["bigint", "smallint", "timestamp without time zone", "timestamp without time zone", "text"]
        _ = F.write("|".join(columns) + "\n" + "|".join(types) + "\n\n")
        for rec in db.data_uploads.search({"status":2}, ["data", "id", "section"]):
            section = reviewer.section_lookup[rec["section"]]
            try:
                sections.add(section)
                for table, newrow, line in section.process(rec["data"]):
                    if (table, newrow) in cols:
                        if cols[table, newrow] != set(line):
                            raise ValueError(f"Schema for id {rec['id']}:{table}:{newrow} does not agree with previous schema")
                    else:
                        cols[table, newrow] = set(line)
                    col_type = db[table].col_type
                    line = "|".join(copy_dumps(line[col], col_type[col]) for col in sorted(line))
                    by_table[table, newrow].append(line)
            except Exception as err:
                status = -3
                comment = str(err).replace("\n", "    ")
            else:
                status = 3
                comment = ""
            timestamp = utc_now_naive().isoformat()
            status_update[rec["section"]][rec["id"]] = (status, timestamp, comment)

        # There are some sections (like gonality propagation) that want to do more
        # processing after all inputs are known.  By default, we use this function
        # just to write status_update to F
        for section_name, ids in status_update.items():
            section = reviewer.section_lookup[rec["section"]]
            section.final_process(ids, F, by_table, cols)

        F.close()
        db.data_uploads.update_from_file(F.name, "id")
        db.data_uploads.cleanup_from_reload()
        os.unlink(F.name)
    timestamp = utc_now_naive().isoformat().replace(":", "-").replace("T", "-").replace(".", "-")
    uploads = []
    for (table, newrows), lines in by_table.items():
        nr = "t" if newrows else "f"
        fname = os.path.join("data", f"{table}_{nr}_{timestamp}")
        columns = sorted(cols[table, newrows])
        col_type = db[table].col_type
        types = [col_type[col] for col in columns]
        with open(fname, "w") as F:
            _ = F.write("|".join(columns) + "\n" + "|".join(types) + "\n\n")
            for line in lines:
                _ = F.write(line + "\n")
        uploads.append((table, newrows, fname))

    # For now we turn off the automatic uploading, for safety's sake as we work out bugs in the uploading code
    #try:
    #    for table, newrows, fname in uploads:
    #        if newrows:
    #            db[table].copy_from(fname)
    #        else:
    #            db[table].update_from_file(fname)
    #except Exception as err:
    #    payload = {"status": -4, "comment": str(err)}
    #else:
    #    payload = {"status": 4}
    #db.data_uploads.update({"id": {"$in": sum(status_update.values(), [])}}, payload)

process_all()
