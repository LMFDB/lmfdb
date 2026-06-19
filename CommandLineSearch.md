Command-line search
===================

The `lmfdb_search` script provides a command-line interface for searching the
[LMFDB](https://www.lmfdb.org/).  By default it connects to the public read-only
mirror `devmirror.lmfdb.xyz`, so you do not need a local copy of the database to
use it.

The script is a thin wrapper around `lmfdb.cmdline_search`; the logic lives in
[`lmfdb/cmdline_search.py`](lmfdb/cmdline_search.py) so that it can be imported
and unit tested (see [`lmfdb/tests/test_cmdline_search.py`](lmfdb/tests/test_cmdline_search.py)).

Requirements
------------

The script runs under Sage's Python (note the `#!/usr/bin/env -S sage -python`
shebang).  Either run it directly

```bash
./lmfdb_search NumberField degree=4
```

or invoke it explicitly:

```bash
sage -python -m lmfdb.cmdline_search NumberField degree=4
```

Usage
-----

```
lmfdb_search TABLE [QUERY] [options]
```

* `TABLE` is either an **LMFDB section** (e.g. `NumberField`, matching the path
  in an LMFDB url) or a **raw database table** (e.g. `nf_fields`).
* `QUERY` constrains the results.  If omitted, every object is returned (subject
  to `--limit`).

### Sections vs. raw tables

Searching a *section* runs the same query parser used by the website, so you can
use the human-friendly search syntax and you get the website's default columns
and download formatting.  Searching a *raw table* gives you direct access to the
underlying psycodict table.

The supported sections are:

| Section | Description |
| --- | --- |
| `L`, `L/rational` | L-functions |
| `ModularForm/GL2/Q/holomorphic` | Classical modular forms |
| `ModularForm/GL2/Q/Maass` | Maass forms |
| `ModularForm/GL2/TotallyReal` | Hilbert modular forms |
| `ModularForm/GL2/ImaginaryQuadratic` | Bianchi modular forms |
| `EllipticCurve/Q` | Elliptic curves over Q |
| `EllipticCurve` | Elliptic curves over number fields |
| `Genus2Curve/Q` | Genus 2 curves over Q |
| `ModularCurve/Q` | Modular curves over Q |
| `HigherGenus/C/Aut` | Higher genus families with automorphisms |
| `Variety/Abelian/Fq` | Abelian varieties over finite fields |
| `Belyi` | Belyi maps |
| `NumberField` | Number fields |
| `padicField` | p-adic fields |
| `Character/Dirichlet/` | Dirichlet characters |
| `ArtinRepresentation` | Artin representations |
| `Motive/Hypergeometric/Q` | Hypergeometric motives over Q |
| `GaloisGroup` | Galois groups |
| `SatoTateGroup` | Sato-Tate groups |
| `Groups/Abstract` | Abstract groups |
| `Lattice` | Integral lattices |

Specifying the query
--------------------

The query format is auto-detected:

* **URL query string** (sections only): the query-string part of an LMFDB url.
  For example `degree=4` matches
  <https://www.lmfdb.org/NumberField/?degree=4>.  Combine constraints with `&`,
  e.g. `degree=2&class_number=17`.
* **JSON dictionary** (sections and raw tables): a
  [psycodict](https://github.com/roed314/psycodict) query, e.g.
  `'{"degree":4}'`.  Detected when the query begins with `{`.
* **Raw SQL** with `--sql`.

A raw table cannot be searched with a url query string (there is no website
parser for it); use a JSON query instead.

The query may also be read from a file with `-i/--input`.

Output formats
--------------

Select the format with `-t/--format` (default `raw`):

| Format | Raw table | Section |
| --- | --- | --- |
| `raw` | ✓ | ✓ |
| `json` | ✓ | ✓ |
| `csv`, `tsv` | ✓ | ✓ |
| `sage`, `gap`, `pari`, `magma`, `oscar`, `text` | | ✓ (via the section's download) |

* `raw` is a compact pipe-delimited format: a header line of column names, a
  line of column types, a blank line, then one line per result.
* The programming-language formats (`sage`, `magma`, etc.) reuse the website's
  download machinery and are therefore only available for sections.

Options
-------

| Option | Description |
| --- | --- |
| `-c, --cols COLS` | Comma-separated list of columns to include in the output. |
| `-l, --limit N` | Maximum number of results (default 50; `-1` for no limit). |
| `--offset N` | Where to start in the list of results. |
| `--sort COLS` | Comma-separated columns to sort by; prefix a column with `-` to reverse it. |
| `--oneper COLS` | Return only one result for each distinct set of values of these columns. |
| `-r, --random` | Return a single object chosen uniformly at random from those matching the query (ignores `--limit`/`--offset`/`--sort`/`--oneper`; not compatible with `--sql`). |
| `-p, --completeness` | Prepend whether the results are known to be complete. |
| `-o, --output FILE` | Write to a file instead of stdout. |
| `-f, --force` | Overwrite the output file if it already exists. |
| `-i, --input FILE` | Read the query from a file. |
| `-s, --sql` | Interpret the query as raw SQL. |
| `-d, --debug` | Raise errors instead of printing a short message. |

> **Note:** because a descending sort column starts with `-`, it must be passed
> with the `=` form so that it is not mistaken for a flag, e.g.
> `--sort=-disc_abs`.

Examples
--------

Number fields of degree 4 (section, url query, default `raw` output):

```bash
./lmfdb_search NumberField degree=4 --limit 5
```

The same search directly against the raw table, as JSON, selecting two columns:

```bash
./lmfdb_search nf_fields '{"degree":4}' --cols label,degree --format json
```

The five degree-4 fields of largest absolute discriminant (descending sort):

```bash
./lmfdb_search nf_fields '{"degree":4}' --cols label,disc_abs --sort=-disc_abs --limit 5
```

Imaginary quadratic fields of class number 17, with a completeness statement:

```bash
./lmfdb_search NumberField 'degree=2&class_number=17' --completeness
```

Export degree-4 number fields as Magma code:

```bash
./lmfdb_search NumberField degree=4 --format magma -o fields.m
```

One representative per Galois group, written as CSV:

```bash
./lmfdb_search nf_fields '{"degree":4}' --oneper galt --cols label,galt --format csv
```

A raw SQL `WHERE` clause against a table:

```bash
./lmfdb_search nf_fields --sql "degree = 4 AND class_number = 5" --cols label,degree,class_number
```

A single random degree-4 number field:

```bash
./lmfdb_search NumberField degree=4 --random
```

Getting help
------------

Run with no arguments (or `help`) to see the option summary.  Pass `help`
followed by a table or section to see its description and the description of
every column, or followed by a table/section and a column name to see that one
column's description:

```bash
./lmfdb_search help nf_fields            # table and all column descriptions
./lmfdb_search help nf_fields degree     # one column's description
./lmfdb_search help NumberField class_number
```
