FAQ
===

Changes
-------

1. What happened to `getDBconnection()`?

   The `getDBconnection()` method has been replaced by an object
   that provides an abstraction layer over the raw database connection.
   You can access this object from Python by importing it: `from lmfdb.db_backend import db`.

1. Why did the databases/collections got renamed?

   Postgres doesn't have the same notion of databases and collections that Mongo does,
   so some renaming was required.  We decided to take advantage of this restructuring to
   add some consistency to the naming scheme.

Database Interface
------------------

1.

Developer configuration
-----------------------

1. Where do I put my passwords?

   When you run `sage -python start_lmfdb.py` for the first time, it will create a configuration file
   `config.ini` in the lmfdb root directory.  In the `postgresql` section it will add the default
   username `lmfdb` and password `lmfdb` which allows for read access to the database.

   In order to get write access to the database, you should change the `user` field to `editor`
   and the `password` field to the editor password.

Adding and modifying data
-------------------------

Note that you need editor priviledges to add, delete or modify data.

1. How do I create a new table?

    The following example creates a new postgres table with name `test_table`
    and three columns: `dim` of type `smallint` (a 2-byte signed integer),
    `discriminant` of type `numeric` (an arbitrary precision integer/decimal)
    and `label` of type `text`.  For more details see the documentation of the
    `create_table` function.

    ```python
    sage: from lmfdb.db_backend import db
    sage: cols = {'smallint': ['dim'], 'numeric': ['discriminant'], 'text': ['label']}
    sage: db.create_table("test_table", cols, label_col="label", sort=['dim', 'discriminant'])
    ```

    Once this table exists, you can access it via the object `db.test_table`,
    which is of type `PostgresTable`.

1. How do I see the type of a column?

    You can access the type of a column using the `col_type` attribute.

    ```python
    sage: db.test_table.col_type['dim']
    'integer'
    ```

1. How do I add a column?

   If you want to add a column to an existing table, use the `add_column` method.

   ```python
   sage: db.test_table.add_column("bad_primes", 'jsonb')
   ```

   This column will be NULL for existing rows.

1. How do I insert new data?

   There are two main methods for adding data to a table.
   The first is the `insert_many` method, which takes a list of
   dictionaries with the data to insert.

   ```python
   sage: L = [{'dim':1, 'discriminant':12, 'label':'1.12.A', 'bad_primes':[2,3]},
              {'dim':2, 'discriminant':30, 'label':'2.30.A', 'bad_primes':[2,3,5]}]
   sage: db.test_table.insert_many(L)
   ```

   The second is `copy_from`, which takes a file with one line per row to be inserted,
   with tabs separating the data on each line.  For large numbers of rows, this method
   will be faster.

   ```python
   sage: db.test_table.copy_from('test.txt', search_cols=['dim', 'discriminant', 'label', 'bad_primes'])
   ```

   Example contents of `test.txt`:

   ```
   1    12      1.12.A  [2,3]
   2    30      2.30.A  [2,3,5]
   ```

1. How do I update data?

   There are a number of methods for updating data.
   One option is `upsert`, which takes a query and dictionary containing values to be set
   and updates a single row satisfying the query.  If no row satisfies the query, a new row
   will be added.

   ```python
   sage: db.test_table.upsert({'discriminant': 12}, {'label':'1.12.B'})
   sage: db.test_table.upsert({'discriminant': 20, 'dim': 2}, {'label':'2.20.B', 'bad_primes':[2,5]})
   ```

   Since upsert only modifies one row at a time, it will be slow if many rows need to be changed.
   Another option is the `rewrite` method.  The first argument is a function
   that processes an existing row and outputs a dictionary giving the changes to be made.
   The second is an optional query allowing you to filter rows from being processed.
   Further keywords are documented in the docstring for the function.

   ```python
   sage: def func(D):
   ....:     D['dim'] += 1
   ....:     old_label = D['label']
   ....:     D['label'] = str(D['dim']) + old_label[:old_label.find('.')]
   ....:     return D
   sage: db.test_table.rewrite(func, {'discriminant':{'$le':25}})
   ```

   Under the hood, this function uses the `reload` method, which is also available for use directly.
   It takes as input files containing the desired data for the table (for basic usage,
   you can just give one file; others are available if your table has an attached extra table, or
   you want to update the stats with the same command).

   ```python
   sage: db.test_table.reload("test.txt", includes_ids=False)
   ```

   Example contents of `test.txt`:

   ```
   2    12      2.12.B  [2,3]
   3    30      3.30.A  [2,3,5]
   3    20      3.20.B  [2,5]
   ```

   The reload method is the fastest option, but requires you to produce an appropriate file.