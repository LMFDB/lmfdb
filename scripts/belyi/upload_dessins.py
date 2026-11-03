r"""
Load the Belyi dessins d'enfants into the LMFDB table belyi_galmap_dessins.

Usage, from the LMFDB root:

    sage -python scripts/belyi/upload_dessins.py DUMP [--out PATH] [--dry-run] [--allow-shrink]
        [--sha256 HEX]

DUMP is a "|"-separated file with columns id, BelyiDB_plabel, DD_images, one
row per Galois orbit and one raw SVG per embedding.  The table was first
loaded on 2026-10-09 from the dump regenerated for LMFDB PR #7189, whose
sha256 is pinned in DUMP_SHA256.  The table itself is now the canonical copy
of the images.  The dump must have that sha256; --sha256 accepts a different,
deliberately regenerated dump.  This script
translates the BelyiDB labels into LMFDB galmap labels via belyi_galmaps,
writes a COPY file, verifies its text[] encoding against postgres, and loads
it into belyi_galmap_dessins (creating the table if it does not exist yet,
reloading it if it does).  A reload that would leave fewer rows than the live
table has is refused, dry run included, unless --allow-shrink is given.

Writing to the database requires write credentials in config.ini; --dry-run
stops after writing and verifying the COPY file and changes no data.
"""

import argparse
import gzip
import hashlib
import os
import re
import sys
from collections import Counter

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../.."))

from lmfdb import db
from lmfdb.utils.psycopg_compat import SQL, DataError

DUMP_SHA256 = "481de914064f56988e9dcc72fc88ec71e8648716b46461b32c2db8a3f0306235"
TABLE_DESCRIPTION = (
    "Dessins d'enfants for Belyi maps: one SVG drawing per embedding of each Galois orbit, "
    "drawn from the permutation triples with Gunnar Brinkmann's map-drawing program "
    "(arXiv:2505.01480)."
)
COL_DESCRIPTION = {
    "label": "LMFDB label of the Belyi map (Galois orbit), as in belyi_galmaps.label",
    "dessins": "SVG drawings of the dessin d'enfant, one per embedding, in the same order as triples_cyc in belyi_galmaps",
}


def read_dump(path):
    """Return a list of (BelyiDB label, list of SVG strings) pairs, one per data line."""
    opener = gzip.open if path.endswith(".gz") else open
    rows = []
    with opener(path, "rt") as F:
        next(F)  # column names
        next(F)  # column types
        for lineno, line in enumerate(F, 3):
            parts = line.rstrip("\n").split("|", 2)
            field = parts[2].strip() if len(parts) == 3 else ""
            if not (field.startswith("{") and field.endswith("}")):
                raise ValueError("line %d of %s is not of the form id|label|{svgs}" % (lineno, path))
            # Not a valid postgres array literal: the elements are unquoted,
            # contain commas and spaces, and inner double quotes are backslashed.
            svgs = [piece.replace('\\"', '"').strip() for piece in re.split(r"(?<=</svg>),", field[1:-1])]
            svgs = [svg for svg in svgs if svg]
            if not svgs:
                raise ValueError("line %d of %s has no svg" % (lineno, path))
            rows.append((parts[1], svgs))
    return rows


def pg_array_literal(elements):
    """Encode a list of strings the way postgres prints a text[] value."""
    # psycodict.encoding.copy_dumps leaves the elements unquoted and escapes
    # inner double quotes only once, which postgres rejects as a malformed
    # array literal, so text[] fields are encoded here instead.
    quoted = ['"' + elt.replace("\\", "\\\\").replace('"', '\\"') + '"' for elt in elements]
    return "{" + ",".join(quoted) + "}"


def copy_escape(value, sep):
    """Apply the escaping COPY uses for a text field with delimiter ``sep``."""
    value = value.replace("\\", "\\\\")
    value = value.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return value.replace(sep, "\\" + sep)


def validate(rows, galmaps):
    errors = []

    def report(complaint, offenders):
        if offenders:
            errors.append("%d %s: %s" % (len(offenders), complaint, sorted(offenders)[:10]))

    report("repeated dump labels",
           [lab for lab, n in Counter(lab for lab, _ in rows).items() if n > 1])
    report("dump labels absent from belyi_galmaps",
           [lab for lab, _ in rows if lab not in galmaps])
    report("rows without one svg per embedding",
           ["%s (%d svgs, %d embeddings)" % (lab, len(svgs), len(galmaps[lab]["triples_cyc"]))
            for lab, svgs in rows
            if lab in galmaps and len(svgs) != len(galmaps[lab]["triples_cyc"])])
    report("rows with a malformed svg",
           [lab for lab, svgs in rows
            if not all(svg.startswith("<svg") and svg.endswith("</svg>") for svg in svgs)])
    if len(rows) <= 1000:
        errors.append("only %d rows in the dump" % len(rows))
    if errors:
        raise ValueError("invalid dump:\n  " + "\n  ".join(errors))


def write_copy_file(out_rows, path, sep="|"):
    with open(path, "w") as F:
        F.write("label%sdessins\ntext%stext[]\n\n" % (sep, sep))
        for label, svgs in out_rows:
            F.write("%s%s%s\n" % (copy_escape(label, sep), sep,
                                  copy_escape(pg_array_literal(svgs), sep)))


COPY_ESCAPE = re.compile(rb"\\(?:([0-7]{1,3})|x([0-9a-fA-F]{1,2})|(.))", re.S)
COPY_CHARS = {b"b": b"\b", b"f": b"\f", b"n": b"\n", b"r": b"\r", b"t": b"\t", b"v": b"\v"}


def copy_unescape(raw):
    """Decode one COPY text-format field the way postgres does, None for NULL."""
    if raw == rb"\N":
        return None

    def char(match):
        octal, hexa, other = match.groups()
        if octal:
            return bytes([int(octal, 8) & 0xFF])
        if hexa:
            return bytes([int(hexa, 16)])
        return COPY_CHARS.get(other, other)

    return COPY_ESCAPE.sub(char, raw).decode()


def read_copy_file(path, sep="|"):
    """Return the data rows of a COPY file, each field as postgres reads it."""
    with open(path, "rb") as F:
        for _ in range(3):  # column names, column types, blank line
            F.readline()
        body = F.read()
    sep = re.escape(sep.encode())
    # A backslash escapes the character after it, newline included.
    field = re.compile(rb"((?:[^\\\n%s]|\\.)*)(%s|\n)" % (sep, sep), re.S)
    rows, row, pos = [], [], 0
    while pos < len(body):
        match = field.match(body, pos)
        if match is None:
            raise ValueError("unterminated row at byte %d of the data in %s" % (pos, path))
        row.append(copy_unescape(match.group(1)))
        if match.group(2) == b"\n":
            rows.append(row)
            row = []
        pos = match.end()
    return rows


def verify_encoding(out_rows, path, sep="|"):
    """Check that postgres reads every row of the COPY file back as out_rows."""
    rows = read_copy_file(path, sep)
    if len(rows) != len(out_rows):
        raise ValueError("%s has %d rows, expected %d" % (path, len(rows), len(out_rows)))
    for (label, svgs), fields in zip(out_rows, rows):
        if len(fields) != 2 or fields[0] != label:
            raise ValueError("the row for %s does not read back as its label and dessins" % label)
        try:
            cur = db._execute(SQL("SELECT %s::text[]"), [fields[1]], silent=True)
        except DataError as err:
            raise ValueError("the dessins of %s are not a valid text[]" % label) from err
        if cur.fetchone()[0] != svgs:
            raise ValueError("encoding of %s does not match postgres" % label)
    return len(rows)


def check_shrink(new_count, allow_shrink):
    """Refuse a reload that would leave belyi_galmap_dessins with fewer rows than it has."""
    live = db._execute(SQL("SELECT count(*) FROM belyi_galmap_dessins")).fetchone()[0]
    print("belyi_galmap_dessins has %d rows; the reload would leave %d" % (live, new_count))
    if new_count < live and not allow_shrink:
        raise ValueError("refusing to shrink belyi_galmap_dessins from %d to %d rows; "
                         "pass --allow-shrink to reload it anyway" % (live, new_count))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dump", help="the dessin dump, gzipped if it ends in .gz")
    parser.add_argument("--out", help="where to write the COPY file")
    parser.add_argument("--dry-run", action="store_true",
                        help="only write and verify the COPY file")
    parser.add_argument("--allow-shrink", action="store_true",
                        help="reload the table even if the dump has fewer rows than it")
    parser.add_argument("--sha256", default=DUMP_SHA256,
                        help="the sha256 the dump must have [default: the reviewed dump's]")
    args = parser.parse_args()

    with open(args.dump, "rb") as F:
        digest = hashlib.sha256(F.read()).hexdigest()
    if digest != args.sha256.lower():
        raise ValueError("%s has sha256 %s, not the expected %s; pass --sha256 to accept a "
                         "deliberately regenerated dump" % (args.dump, digest, args.sha256))
    print("accepted %s with sha256 %s" % (args.dump, digest))
    rows = read_dump(args.dump)
    galmaps = {rec["BelyiDB_label"]: rec for rec in
               db.belyi_galmaps.search({}, projection=["label", "BelyiDB_label", "triples_cyc"])}
    validate(rows, galmaps)
    out_rows = sorted((galmaps[lab]["label"], svgs) for lab, svgs in rows)

    base = args.dump[:-3] if args.dump.endswith(".gz") else args.dump
    path = args.out or base + ".copy.txt"
    write_copy_file(out_rows, path)
    print("wrote %s (%d rows)" % (path, len(out_rows)))
    print("verified the text[] encoding against postgres for %d rows" % verify_encoding(out_rows, path))
    exists = "belyi_galmap_dessins" in db.tablenames
    if exists:
        check_shrink(len(out_rows), args.allow_shrink)
    if args.dry_run:
        print("dry run: the database was not modified")
        return

    if not exists:
        db.create_table("belyi_galmap_dessins",
                        {"text": ["label"], "text[]": ["dessins"]},
                        "label",
                        table_description=TABLE_DESCRIPTION,
                        col_description=COL_DESCRIPTION,
                        sort=["label"])
        db.belyi_galmap_dessins.copy_from(path)
    else:
        db.belyi_galmap_dessins.reload(path)
    print("belyi_galmap_dessins now has %d rows" % db.belyi_galmap_dessins.count())


if __name__ == "__main__":
    main()
