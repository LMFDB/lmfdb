"""
This file provides an interface for logged in users to upload data for approval by LMFDB editors.

Validation occurs in several stages, with the progression indicated by status column in the uploads table.
* Some inexpensive validation steps are done on submission (proper formatting, labels exist, etc).  Entries passing this step are added to the uploads table with status 0.
* An additional validation step is run on a server (anything that might take a nontrivial amount of computation).  Entries passing this step are graduated to status 1; failures are marked with status -1.
* Entries passing this step are checked by a human editor; acceptance earns status 2 and failure is marked with status -2.
* Approved entries are then added to the appropriate table by another script run on a server (since this step may also involve nontrivial computation, like with gonality bounds).  Entries passing this step are marked with status 3; failures with -3.  A successful run of this step produces file(s) for use with copy_from on appropriate tables.
* Finally, a script executes copy_from.  Failure here is unexpected and marked with -4 (due to failure in Postgres loading the file); success is marked with 4.
* While in stage 0, 1 or 2, uploads can be withdrawn by the submitter.  If so, they will be marked with status -5.
"""

import os
import re
import csv
import io
import codecs
import tempfile
from lmfdb.utils.datetime_utils import utc_now_naive
from flask import request, flash, send_file, render_template
from flask_login import current_user
from sage.misc.lazy_attribute import lazy_attribute
from sage.rings.integer_ring import ZZ
from lmfdb.utils import flash_error, flash_info, pluralize
from psycodict.encoding import copy_dumps
from lmfdb import db

class UploadBox():
    def __init__(self, name, label, knowl, **kwds):
        self.name = name
        self.label = label
        self.knowl = knowl
        for key, val in kwds.items():
            setattr(self, key, val)

    def validate(self, value):
        if getattr(self, "remove_spaces", None):
            value = value.replace(" ", "")
        if getattr(self, "integer", False):
            return ZZ(value)
        if getattr(self, "natural_or_range", False):
            # Non-negative integer or a range of them
            if value.isdigit():
                return value
            if value.count("-") == 1:
                a, b = value.split("-")
                if a and a.isdigit() and b and b.isdigit():
                    return value
            raise ValueError(rf"{self.name} must be a positive integer or range like 2-4; '{value}' is invalid")
        table = getattr(self, "label_for", None)
        if table:
            if db[table].label_exists(value):
                return value
            raise ValueError(f"There is no {self.name} with label {value} in {table}")
        table = getattr(self, "name_or_label_for", None)
        if table:
            if db[table].label_exists(value):
                return value
            label = db[table].lucky({"name": value}, "label")
            if label is not None:
                return label
            raise ValueError(f"There is no {self.name} with name or label {value} in {table}")
        matcher = getattr(self, "re", None)
        if matcher:
            if isinstance(matcher, tuple):
                matcher, description = matcher
                description = f" ({description})"
            else:
                description = ""
            match = matcher.fullmatch(value)
            if match:
                return value
            raise ValueError(f"{self.name} {value} does not match regular expression {matcher.pattern}{description}")

    def display(self, value):
        # Used in reviewing uploads
        if getattr(self, "mathmode", None):
            return f"${value}$"
        linker = getattr(self, "label_linker", None)
        if linker:
            return linker(value)

        # default is to just display the provided value as is.
        return value

class UTextBox(UploadBox):
    def html(self):
        if hasattr(self, "width"):
            width = f'style="width: {self.width}px" '
        else:
            width = ""
        return f'<input type="text" name="{self.name}" {width}/>'

reference_re = re.compile(r"arXiv:(?P<arxiv>([a-z\-]+/\d+)|(\d{4}\.\d+(v\d+)?))|MR:(?P<mr>\d+)|doi:(?P<doi>.+)")
class UReferenceBox(UTextBox):
    def validate(self, value):
        if reference_re.fullmatch(value):
            return value
        raise ValueError("Reference not in required format (arXiv:, MR: or doi:)")

    def display(self, value):
        m = reference_re.fullmatch(value)
        if not m:
            return "Invalid"
        if m.group("arxiv"):
            url = "https://arxiv.org/abs/" + m.group("arxiv")
        elif m.group("mr"):
            url = "https://www.ams.org/mathscinet-getitem?mr=" + m.group("mr")
        elif m.group("doi"):
            url = "https://doi.org/" + m.group("doi")
        return f'<a href="{url}">{value}</a>'

class USelectBox(UploadBox):
    def __init__(self, name, label, knowl, options, **kwds):
        self.options = options
        super().__init__(name, label, knowl, **kwds)

    def html(self):
        keys = [f'name="{self.name}"']
        if hasattr(self, "width"):
            keys.append(f'style="width: {self.width}px"')
        opts = []
        for value, display in self.options:
            if value is None:
                value = ""
            else:
                value = f'value="{value}"'
            opts.append(f"<option {value}>{display}</option>")
        return "\n            <select %s>\n%s\n          </select>\n" % (
            " ".join(keys),
            "".join("\n" + " " * 14 + opt for opt in opts),
        )

    def validate(self, value):
        opts = [val for val, display in self.options]
        if value in opts:
            if getattr(self, "no_empty", None) and not value:
                raise ValueError(f"Must specify {self.name}")
            if getattr(self, "integer", False):
                return ZZ(value)
            return value
        raise ValueError(f"{value} is not a legal option for {self.name} (must be one of {','.join(opts)})")

    def display(self, value):
        # Option names are all strings
        value = str(value)
        for val, display in self.options:
            if val == value:
                return display
        return "Invalid option"

class UTextArea(UploadBox):
    def __init__(self, name, label, knowl, cols=30, rows=3, **kwds):
        self.cols = cols
        self.rows = rows
        super().__init__(name, label, knowl, **kwds)

    def html(self):
        return f'<textarea name="{self.name}" cols="{self.cols}" rows="{self.rows}"></textarea>'

    def validate(self, value):
        if value.strip():
            value = value.strip().split("\n")
        else:
            value = []
        return [super().validate(x) for x in value]

# The following boxes are used for displaying information for reviewing potential uploads
class StatusBox(UploadBox):
    def __init__(self):
        self.statuses = {
            -5: "Withdrawn",
            -4: "Unexpected error",
            -3: "Processing failed",
            -2: "Negatively reviewed",
            -1: "Verification failed",
            0: "Verification pending",
            1: "Needs review",
            2: "Processing pending",
            3: "Upload pending",
            4: "Upload finished",
        }
        super().__init__("status", "Status", "upload.status")

    def display(self, value):
        return self.statuses.get(value, "Invalid status")

class SubmitterBox(UploadBox):
    def __init__(self):
        super().__init__("submitter", "Submitter", "upload.submitter")

class UpdatedBox(UploadBox):
    def __init__(self):
        super().__init__("updated", "Updated", "upload.recent_update")

    def display(self, value):
        return '{d:%b} {d.day}, {d.hour}:{d.minute:02}'.format(d=value)

class CommentBox(UploadBox):
    def __init__(self):
        super().__init__("comment", "Comment", "upload.comment")

class UploadSection():
    version = 0 # Increment if there is a data format change
    # Override the following in subclass, or set in __init__
    name = None
    title = None
    intro = None
    inputs = []
    offer_csv = True
    csv_template_url = None

    def __init__(self, **kwds):
        for key, val in kwds.items():
            setattr(self, key, val)

    def validate(self, rec):
        """
        This function is called at input time when a user uploads data,
        performating basic validation but nothing that takes a long time.

        Failure is immediately reported to the user who attempted to upload data.
        """
        for box in self.inputs:
            rec[box.name] = box.validate(rec[box.name])
        return rec

    def verify(self, rec):
        """
        This function is called by a cron job and is allowed to perform more
        complicated verifications (e.g. calling Magma and computing the Galois image
        of an elliptic curve).

        INPUT:

        - ``rec`` -- the data uploaded and stored in the ``data`` column in the
          ``data_uploads`` table.

        OUTPUT:

        No output, but an error is raised if verification fails; the error message will be
        stored in the ``comment`` column.
        """
        raise NotImplementedError(f"verify method not implemented for {self.name}")

    def process(self, rec):
        """
        This function is called by a cron job after human approval of a data upload.
        It should split the upload into specific tables and the columns to be changed
        therein.

        INPUT:

        - ``rec`` -- the data uploaded and stored in the ``data`` column in the
          ``data_uploads`` table.

        OUTPUT:

        A list of triples ``(table, newrow, line)``, where

        - ``table`` is the name of a database table,
        - ``newrow`` is a boolean: whether this line should be added as a new row
            (versus updating an existing row)
        - ``line`` -- a dictionary with columns as keys and values that can be accepted
            by copy_dumps.  IMPORTANT: the set of columns must depend only on the
            pair ``(table, newrow)``.
        """
        raise NotImplementedError(f"process method not implemented for {self.name}")

    def final_process(self, ids, F, by_table=None, cols=None):
        """
        Record the new statuses to file; called after all uploads have been processed in lmfdb/uploads/process.py.  Included for some sections to override so that they can do additional work at this stage.

        INPUT:

        - ``ids`` -- a dictionary with keys the ids from the data_uploads table that are being processed
            by this section, and value the triple ``(status, timestamp, comment)`` determined after
            the return of the process method on this upload row.
        - ``F`` -- an open file handle, used to write updates to the data_uploads table, with columns
            ["id", "status", "processed", "updated", "comment"]

        The later arguments are not used by default (they are present since GonalityBounds needs to update
        these dictionaries):

        - ``by_table`` -- a dictionary, with keys (table, newrow) and values a list of lines,
            as output by the process method.
        - ``cols`` -- a dictionary with keys (table, newrow) and values the set of columns for that pair
        """
        # Default behavior: just write the contents of ids to F.
        # The other inputs are only present for non-default behavior;
        # see GonalityBounds in modular_curves/upload.py
        for upid, (status, timestamp, comment) in ids.values():
            _ = F.write(f"{upid}|{status}|{timestamp}|{timestamp}|{comment}\n")

    @lazy_attribute
    def header(self):
        return [re.sub('[^0-9a-zA-Z ]+', '', box.label).replace("mathbb", "") for box in self.inputs]

    @lazy_attribute
    def header_dict(self):
        return dict(zip(self.header, self.inputs))

    def parse_csv(self, stream):
        reader = csv.reader(stream)
        for i, row in enumerate(reader):
            if i == 0:
                # Header row
                if set(row) != set(self.header):
                    raise ValueError(f"First row of CSV file must match: {', '.join(self.header)}")
                header = [self.header_dict[x] for x in row]
            else:
                if any(x for x in row):
                    if len(row) != len(header):
                        raise ValueError(f"Row {i} of CSV file has {len(row)} entries but header has {len(header)}")
                    yield self.validate({box.name: val for box, val in zip(header, row)})

    def parse_form(self, form):
        form = dict(form)
        return [self.validate({box.name: form[box.name] for box in self.inputs})]

    def save(self, data):
        with tempfile.NamedTemporaryFile("w", delete=False) as F:
            columns = ["section", "status", "submitter", "data", "submitted", "verified", "reviewed", "processed", "updated", "version", "comment"]
            types = ["text", "smallint", "text", "jsonb", "timestamp without time zone", "timestamp without time zone", "timestamp without time zone", "timestamp without time zone", "timestamp without time zone", "smallint", "text"]
            _ = F.write("|".join(columns) + "\n" + "|".join(types) + "\n\n")
            timestamp = utc_now_naive().isoformat()
            for rec in data:
                _ = F.write(f"{self.name}|0|{current_user.id}|{copy_dumps(rec, 'jsonb')}|{timestamp}|\\N|\\N|\\N|{timestamp}|{self.version}|\n")
            F.close()
            db.data_uploads.copy_from(F.name)
            os.unlink(F.name)

    def csv_template(self):
        filename = f"{self.name}.csv"
        # csv.writer needs a StringIO but send_file needs a BytesIO
        sIO = io.StringIO()
        bIO = io.BytesIO()
        writer = csv.writer(sIO)
        writer.writerow(self.header)
        bIO.write(sIO.getvalue().encode("utf-8"))
        bIO.seek(0)
        sIO.close()
        return send_file(bIO, download_name=filename, as_attachment=True, mimetype="text/csv")

    def review_cols(self, user_shown, statuses):
        # By default, we include the status (if there is more than one status) and submitter at the beginning and the timestamp when the upload was most recently changed at the end.
        cols = self.inputs + [UpdatedBox(), CommentBox()]
        if user_shown != current_user.id:
            cols.insert(0, SubmitterBox())
        if len([x for x in statuses if x[2]]) != 1:
            cols.insert(0, StatusBox())
        return cols


class Uploader():
    # Override in subclass
    title = None
    bread = None
    learnmore = None

    def __init__(self, sections):
        self.sections = sections
        self.section_lookup = {section.name: section for section in sections}

    def render(self):
        if request.method == "POST":
            if current_user.is_authenticated:
                submit = request.form.get("submit", "")
                try:
                    if submit.endswith("_file"):
                        section = self.section_lookup[submit[:-5]]
                        keys = list(request.files)
                        if len(keys) != 1:
                            raise ValueError("No file submitted")
                        F = request.files[keys[0]]
                        # If the user does not select a file, the browser submits an
                        # empty file without a filename.
                        if not F.filename:
                            raise ValueError("No file selected")
                        data = list(section.parse_csv(codecs.getreader("utf-8")(F.stream)))
                    else:
                        section = self.section_lookup[submit]
                        data = section.parse_form(request.form)
                    section.save(data)
                except Exception as err:
                    flash_error(str(err))
                else:
                    flash("Successfully uploaded data")
            else:
                flash_error("You must be logged in to upload data")
        return render_template(
            "upload_data.html",
            uploader=self,
            title=self.title,
            bread=self.bread,
            learnmore=self.learnmore)

    def review(self, info, reviewer, userid):
        """
        Change status on a set of data uploads

        INPUT:

        - ``info`` -- the contents of the review form from user-upload.html
        - ``reviewer`` -- whether the current user is allowed to review knowls
        - ``userid`` -- the username of the current user
        """
        if info["submit"] == "approve":
            new_status = 2
            desc = "approved"
        elif info["submit"] == "reject":
            new_status = -2
            desc = "rejected"
        elif info["submit"] == "withdraw":
            new_status = -5
            desc = "withdrawn"
        else:
            new_status = -10
        comment = info.get("comment", "").strip().replace("\n", "    ")
        if (reviewer and new_status != -10) or new_status == -5:
            # Modification allowed
            ids = [int(x[7:]) for x in info if x.startswith("select_") and x[7:].isdigit()]
            if ids:
                if new_status == -5 and not all(rec["submitter"] == userid and (0 <= rec["status"] < 3) for rec in db.data_uploads.search({"id":{"$in":ids}}, "submitter")):
                    flash_error("You can only withdraw your own uploads, and only before final processing")
                elif new_status in [2, -2] and not all(status == 1 for status in db.data_uploads.search({"id":{"$in":ids}}, "status")):
                    flash_error("You must select only rows that need review")
                else:
                    t0 = utc_now_naive()
                    payload = {"status": new_status, "reviewed": t0, "updated": t0}
                    if comment:
                        payload["comment"] = comment
                    db.data_uploads.update({"id":{"$in":ids}}, payload)
                    flash_info(f"{pluralize(len(ids), 'upload')} successfully {desc}")
        else:
            flash_error("Invalid submit value (you may not have sufficient permissions)")

    def show_uploads(self, info, reviewing, user_shown):
        """
        Return a set of data uploads to display for a user

        INPUT:

        - ``info`` -- the arguments passed in from user-uploads.html, either via GET or POST, including data on which statuses should be shown
        - ``reviewing`` -- whether the user is reviewing (this affects defaults for which statuses to show)
        - ``user_shown`` -- a username, or empty to show all usernames

        OUTPUT:

        - A dictionary indexed by section name, with values the uploads in that section satisfying the requested constraints
        """
        statuses = [
            (-5, "Withdrawn", False),
            (-4, "Unexpected error", True),
            (-3, "Processing failed", not reviewing),
            (-2, "Negatively reviewed", not reviewing),
            (-1, "Verification failed", not reviewing),
            (0, "Verification pending", not reviewing),
            (1, "Needs review", True),
            (2, "Processing pending", not reviewing),
            (3, "Upload pending", not reviewing),
            (4, "Upload finished", False),
        ]
        if "submit" in info:
            # The user had a chance to change the selection boxes, so we use the provided values for which statuses to display
            for i, (a,b,c) in enumerate(statuses):
                statuses[i] = (a, b, info.get(str(a)) == "on")

        # Construct the query, specifying a submitter and/or upload status
        results = {}
        has_unexpected = False
        if any(c for a, b, c in statuses):
            query = {}
            query["section"] = {"$in": list(self.section_lookup)}
            query["status"] = {"$in": [int(a) for a, b, c in statuses if c]}
            if user_shown:
                query["submitter"] = user_shown

            for rec in db.data_uploads.search(query, ["id", "section", "status", "submitter", "data", "updated", "comment"]):
                section = rec["section"]
                if section not in results:
                    results[section] = []
                has_unexpected = has_unexpected or (rec["status"] == -4)
                data = rec.pop("data")
                data.update(rec)
                results[section].append(data)
        if not has_unexpected and "submit" not in info:
            # By default we prefer to just show Needs Review, since that will prevent the "Status" column from being shown
            # But we want to show Unexpected Errors if they exist
            # So if we didn't see an unexpected error we turn off that checkbox
            statuses[1] = (-4, "Unexpected error", False)
        return results, statuses

    def needs_review(self):
        n = db.data_uploads.stats._slow_count({"section":{"$in":[section.name for section in self.sections]}, "status": 0}, record=False)
        if n:
            return str(n)
        else:
            return ""
