# -*- coding: utf-8 -*-
"""
This file provides an interface for logged in users to upload data for approval by LMFDB editors.

Validation occurs in several stages, with the progression indicated by status column in the uploads table.
* Some inexpensive validation steps are done on submission (proper formatting, labels exist, etc).  Entries passing this step are added to the uploads table with status 0.
* An additional validation step is run on a server (anything that might take a nontrivial amount of computation).  Entries passing this step are graduated to status 1; failures are marked with status -1.
* Entries passing this step are checked by a human editor; acceptance earns status 2 and failure is marked with status -2.
* Approved entries are then added to the appropriate table by another script run on a server (since this step may also involve nontrivial computation, like with gonality bounds).  Entries passing this step are marked with status 3; failures with -3.  A successful run of this step produces file(s) for use with copy_from on appropriate tables.
* Finally, a script executes copy_from.  Failure here is unexpected and marked with -4 (due to failue in Postgres loading the file); success is marked with 4.
* While in stage 0, 1 or 2, uploads can be withdrawn by the submitter.  If so, they will be marked with status -5.
"""

import os
import re
import csv
import codecs
import tempfile
from datetime import datetime
from flask import request, flash, send_file, render_template
from flask_login import current_user
from sage.misc.lazy_attribute import lazy_attribute
from sage.rings.integer_ring import ZZ
from lmfdb.utils import flash_error
from lmfdb.backend.encoding import copy_dumps
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
            raise ValueError(r"{self.name} must be a positive integer or range like 2-4; '{value}' is invalid")
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
            url = linker(value)
            return f'<a href="{url}">{value}</a>'

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
        keys = ['name="{self.name}"']
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
        opts = [val for (val, display) in self.options]
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

        Failure is immediately reported to the user who attemped to upload data.
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
        """
        raise NotImplementedError(f"process method not implemented for {self.name}")

    @lazy_attribute
    def header(self):
        return [re.sub('[^0-9a-zA-Z ]+', '', box.label).replace("mathbb", "") for box in self.inputs]

    @lazy_attribute
    def header_dict(self):
        return {name: box for (name, box) in zip(self.header, self.inputs)}

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
                    yield self.validate({box.name: val for (box, val) in zip(header, row)})

    def parse_form(self, form):
        form = dict(form)
        return [self.validate({box.name: form[box.name] for box in self.inputs})]

    def save(self, data):
        with tempfile.NamedTemporaryFile("w", delete=False) as F:
            columns = ["section", "status", "submitter", "data", "submitted", "verified", "reviewed", "processed", "updated", "version", "comment"]
            types = ["text", "smallint", "text", "jsonb", "timestamp without time zone", "timestamp without time zone", "timestamp without time zone", "timestamp without time zone", "timestamp without time zone", "smallint", "text"]
            _ = F.write("|".join(columns) + "\n" + "|".join(types) + "\n\n")
            timestamp = datetime.utcnow().isoformat()
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
        cols = self.inputs + [UpdatedBox()]
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

    def review(self):
        if current_user.is_admin():
            if request.method == "POST":
                submit = request.form.get("submit", "")
                try:
                    n = 0
                    approving = submit.endswith("_approve")
                    if approving:
                        pass
                except Exception as err:
                    flash_error(str(err))
                else:
                    if approving:
                        flash("Successfully approved {n} submissions")
                    else:
                        flash("Successfully rejected {n} submissions")
            else:
                return render_template(
                    "review_uploads.html",
                    uploader=self,
                    title="Review uploads")
        else:
            flash_error("You must be an admin to review data uploads")
            return redirect(url_for("index"))

    def needs_review(self):
        n = db.data_uploads.count({"section":{"$in":[section.name for section in self.sections]}, "status": 0})
        if n:
            return str(n)
        else:
            return ""
