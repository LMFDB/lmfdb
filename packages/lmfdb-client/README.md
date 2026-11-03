# lmfdb-client

A Python interface to the [L-functions and modular forms database](https://www.lmfdb.org) (LMFDB).  It uses the [psycodict](https://github.com/roed314/psycodict) library, which provides a dictionary-based approach to interacting with SQL databases and is in turn built upon [psycopg](https://www.psycopg.org/psycopg3/docs/).

This package replaces [lmfdb-lite](https://github.com/roed314/lmfdb-lite).  It is built from the [LMFDB repository](https://github.com/LMFDB/lmfdb), and the LMFDB website uses it for its own connection, so it shares the website's connection settings and conventions.

## Install

```
pip install lmfdb-client
```

It works with any Python 3.9 or later; in [SageMath](https://www.sagemath.org), install it with `sage -pip install lmfdb-client` (see "Using Sage" below).  If you used lmfdb-lite, uninstall it first (`pip uninstall lmfdb-lite`): lmfdb-client also provides its `lmf` module, so that `from lmf import db` keeps working.

## Usage

```python
>>> from lmfdb_client import db
>>> sorted(set(name.split("_")[0] for name in db.tablenames))
['artin', 'av', 'belyi', 'bmf', 'char', 'cluster', 'data', 'ec', 'fq', 'g2c', 'gps', 'halfmf', 'hecke', 'hgcwa', 'hgm', 'hmf', 'hmsurfaces', 'inv', 'lat', 'lf', 'lfunc', 'maass', 'mf', 'modcurve', 'modlgal', 'modlmf', 'nf', 'noncong', 'pg', 'quaternion', 'shimcurve', 'shimura', 'smf', 'test', 'weil']
>>> db.gps_conj_classes.search_cols
['aut_label', 'centralizer', 'counter', 'group_counter', 'group_order', 'label', 'order', 'powers', 'representative', 'size']
```

Importing `lmfdb_client` does not connect: the connection is made the first time `db` is used.

A web-based view of the LMFDB's available tables is available [here](https://beta.lmfdb.org/api/); clicking on a table name gives the first few records in that table as well as a link to the schema for the table.  The descriptions of tables and columns are also available from Python:

```python
>>> db.ec_curvedata.description()
>>> db.ec_curvedata.column_description("conductor")
```

### Searching

The `search` method is one of the two main public interfaces for performing SELECT queries, intended for finding multiple results.  It takes as input a query dictionary (see the Queries section below for details) and a projection (a column name or list of column names) and returns an iterator as output.  Each entry in the output is either the value of the column (if a single column was specified) or a dictionary with column names as keys.

```python
>>> list(db.gps_groups.search({"order": 8}, "name"))
['C8', 'C2*C4', 'D4', 'Q8', 'C2^3']
>>> list(db.ec_curvedata.search({"rank": 1}, ["lmfdb_label", "conductor", "ainvs"], limit=5))
[{'lmfdb_label': '37.a1', 'conductor': 37, 'ainvs': [0, 0, 1, -1, 0]},
 {'lmfdb_label': '43.a1', 'conductor': 43, 'ainvs': [0, 1, 1, 0, 0]},
 {'lmfdb_label': '53.a1', 'conductor': 53, 'ainvs': [1, -1, 1, 0, 0]},
 {'lmfdb_label': '57.a1', 'conductor': 57, 'ainvs': [0, -1, 1, -2, 2]},
 {'lmfdb_label': '58.a1', 'conductor': 58, 'ainvs': [1, -1, 0, -1, 1]}]
```

If only a single result is required, you can also use the `lucky` method, which takes similar inputs.

```python
>>> db.lf_fields.lucky({"galois_label":"4T4"}, ["p", "n", "coeffs"])
{'p': 2, 'n': 4, 'coeffs': [2, 0, 2, 2, 1]}
```

If you know the label for the object you can use the `lookup` method.

```python
>>> db.nf_fields.lookup("6.0.9747.1", "regulator")
0.601543105945
```

### Random objects

You can get a random object from a table (the projection defaults to the label in this case).

```python
>>> db.gps_groups.random({"order": 256})
'256.45342'
>>> db.gps_groups.random({"order": 256}, ["label", "exponent", "nilpotency_class", "aut_order", "center_label"])
{'label': '256.48589', 'exponent': 4, 'nilpotency_class': 2, 'aut_order': 32768, 'center_label': '8.5'}
```

If you want many random objects, `random_sample` can be more efficient (different modes have different efficiency/randomness tradeoffs).

```python
>>> from collections import Counter
>>> Counter(db.gps_groups.random_sample(0.01, {"order": 256}, "nilpotency_class"))
Counter({2: 325, 3: 236, 4: 18, 5: 4, 6: 2})
>>> Counter(db.gps_groups.search({"order": 256}, "nilpotency_class"))
Counter({1: 22, 2: 31742, 3: 21325, 4: 2642, 5: 320, 6: 38, 7: 3})
```

### Statistics

Basic statistical quantities are available through built-in functions; of course you can compute more complicated statistics in Python.

```python
>>> db.mf_newforms.count()
1141508
>>> db.mf_newforms.count({"weight": 1})
19306

>>> db.ec_curvedata.max("rank")
5
>>> db.ec_curvedata.max("rank", {"torsion_order": 8})
2

>>> db.nf_fields.min("regulator")
0.205216461048

>>> db.g2c_curves.distinct("end_alg")
['CM', 'M_2(Q)', 'Q', 'Q x Q', 'RM']

>>> db.ec_nfcurves.count_distinct("torsion_order")
29

>>> db.ec_curvedata.sum("rank") / db.ec_curvedata.count()
0.7829141621160285
```

### Queries

Many methods (most notably `search` and `lucky`) take dictionaries that specify the WHERE clause in an SQL query, determining which rows of the table are returned.  The query language used in these dictionaries does not allow for arbitrary criteria, but instead a more limited set of clauses tailored to support the LMFDB's search webpages.  See the [query language specification](https://github.com/roed314/psycodict/blob/master/QueryLanguage.md) for more details.

### Using SQL directly

You can run your own SQL commands directly using the underlying [psycopg](https://www.psycopg.org/psycopg3/docs/) engine.  This can be useful if you want to run queries that are not possible with the query language (e.g. joins, or comparing different columns in the same table).

```python
>>> from psycodict import SQL, Identifier
>>> cur = db._execute(SQL("SELECT label, name FROM gps_groups WHERE {0} = %s").format(Identifier("order")), [8])
>>> list(cur)
[('8.2', 'C2*C4'), ('8.5', 'C2^3'), ('8.1', 'C8'), ('8.3', 'D4'), ('8.4', 'Q8')]
```

## Using Sage

lmfdb-client works in plain Python, where numeric columns come back as Python `int`s and `float`s.  When it is used from [SageMath](https://www.sagemath.org) (a Sage session, a Sage notebook, or `sage -python`), the values come back as Sage objects instead: integers are Sage `Integer`s, and decimals are Sage real numbers whose precision matches the number of digits stored (and which print exactly as stored).  Sage objects (integers, rationals, real and complex numbers, number field elements, polynomials, vectors...) can also be used in queries and when uploading data.

## Configuration

By default lmfdb-client connects, read-only, to `devmirror.lmfdb.xyz`, a public mirror of the LMFDB.  The settings are read from a configuration file, which is created with the default values on first use.  It is the first of:

- the file named by the `LMFDB_CONFIG` environment variable;
- `config.ini` in the current directory, if it exists (so running from the root of an LMFDB checkout uses the website's configuration);
- `config.ini` in the LMFDB home directory: `LMFDB_HOME` if set, otherwise `~/.lmfdb`.

A `secrets.ini` next to the configuration file, in the same format, overrides its values, so that passwords can be kept out of the configuration file.  The configuration file looks like

```ini
[postgresql]
host = devmirror.lmfdb.xyz
port = 5432
user = lmfdb
password = lmfdb
dbname = lmfdb
keepalives = 1
keepalives_idle = 30
keepalives_interval = 10
keepalives_count = 5

[logging]
slowcutoff = inf
slowlogfile = slow_queries.log
editor =
```

Setting `slowcutoff` to a number of seconds logs slower queries to `slowlogfile` (by default in `logs/` in the LMFDB home directory) and prints them.  To use a configuration from your own code, pass it when connecting:

```python
>>> from lmfdb_client import db
>>> from lmfdb_client.config import Configuration
>>> db.connect(Configuration())
```

or give `db.connect` a dictionary such as `{"postgresql_options": {"host": ..., "port": ..., "user": ..., "password": ..., "dbname": ...}}`.

## Making changes

Editors with write access make data changes through the same interface (`insert_many`, `update_from_file`, `create_table`, ...), using the editor credentials in their `secrets.ini`.  Changes are recorded together with the editor's LMFDB username (the `editor` setting, or asked for on the first change), and before large changes lmfdb-client checks that the database servers have enough disk space.  Table and column descriptions, which are stored as knowls, can be read here but are edited from a checkout of the [LMFDB repository](https://github.com/LMFDB/lmfdb), which also runs the data verification checks.

## Troubleshooting

If the connection to the SQL database is broken, you may need to manually reset it using `db.reset_connection()`.

If a query is takes an unexpectedly long time, you can see what the underlying SQL command being executed is.

```python
>>> db.nf_fields.analyze({"ramps":{"$contains":[3,5,11]}}, "label")
b'SELECT "class_group", "class_number", "cm", "coeffs", "conductor", "degree", "disc_abs", "disc_rad", "disc_sign", "embeddings_gen_imag", "embeddings_gen_real", "gal_is_abelian", "gal_is_cyclic", "gal_is_solvable", "galois_disc_exponents", "galois_label", "galt", "grd", "index", "inessentialp", "is_galois", "is_minimal_sibling", "iso_number", "label", "local_algs", "minimal_sibling", "monogenic", "num_ram", "r2", "ramps", "rd", "regulator", "relative_class_number", "subfield_mults", "subfields", "torsion_order", "used_grh" FROM "nf_fields" WHERE "ramps" @> ARRAY[ARRAY[3,5,11]]::numeric[] ORDER BY "degree", "disc_abs", "disc_sign", "iso_number" LIMIT 1000'
Limit  (cost=0.56..31787.91 rows=1000 width=627) (actual time=328.322..8175.915 rows=1000 loops=1)
  ->  Index Scan using nf_fields_degree_disc_abs_disc_sign_iso_number on nf_fields  (cost=0.56..10823431.84 rows=340495 width=627) (actual time=328.320..8175.348 rows=1000 loops=1)
        Filter: (ramps @> '{{3,5,11}}'::numeric[])
        Rows Removed by Filter: 287074
Planning Time: 54.861 ms
Execution Time: 8176.447 ms
```

## Development

This package lives in `packages/lmfdb-client` in the [LMFDB repository](https://github.com/LMFDB/lmfdb); an LMFDB checkout installs it in editable mode (`sage -pip install -r requirements.txt`).  Its tests are in `packages/lmfdb-client/tests`.
