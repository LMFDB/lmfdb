FAQ
===

Changes
-------

1. What happened to `getDBconnection()`?

   The `getDBconnection()` method has been replaced by an object
   that provides an abstraction layer over the raw database connection.
   You can access this object from Python by importing it:
   `from lmfdb import db`.

1. What's an overview of the changes?

   There is a new file, `lmfdb/backend/database.py`, containing the
   main components of the new interface to the Postgres database.
   Postgres is a mature, open-source implementation of SQL.  One of
   the main differences is that Postgres is a strongly-typed
   relational database, meaning that every table has a schema with
   types for each column.  In contrast, Mongo allows you to insert
   arbitrary documents into a collection.  This flexibility can be
   useful, but it also causes performance headaches as the size of the
   database grows.

   Postgres enables queries that weren't possible before, especially
   around subsets (for example, searching for number fields with
   specified ramification is now feasible).  Moreover, SQL allows for
   queries across tables that weren't possible in Mongo, though this
   isn't supported by the LMFDB website.

   For the most part, the front-end experience will be very similar.
   One change that you will see is some queries will now report a
   total of "at least 1000".  This results from a limitation in the
   postgres storage mechanism that can make getting exact counts for
   queries much slower than retrieving the first 50 rows.  If you care
   about the number of results, you can click on "at least 1000" and
   it will compute the count for you.

   The implementation of search functions across various parts of the
   lmfdb has also been standardized, and some common features have
   been refactored into a common codebase.

1. Why did the databases/collections get renamed?

   Postgres doesn't have the same notion of databases and collections
   that Mongo does, so some renaming was required.  We decided to take
   advantage of this restructuring to add some consistency to the
   naming scheme.

1. Why do I still see messages about mongo when I start the LMFDB?

   Classical modular forms are still using mongo.  We're working on
   revising them to use postgres, but in the mean time we're still
   connecting to a mongo database.

Database Interface
------------------

1. How do I interact with the database as a developer?

   There are three main objects in the database interface: the overall
   database interface (`db`, of type `PostgresDatabase`) which
   contains tables (e.g. `db.nf_fields` of type `PostgresTable`), each
   of which has a statistics object (e.g. `db.nf_fields.stats` of type
   `PostgresStatsTable`).

   Each section of the lmfdb will generally rely on one (or perhaps a
   few) table, and most of the methods of interest are on the table
   objects.

1. How do I find the names of all of the tables?

   The list `db.tablenames` is a list of the tables (with the
   exception of knowls, users, and meta tables).

1. How do I determine what columns are in a table?

   Each table has a `col_type` dictionary, whose keys are column names
   and values are column types.  For example,
   ```python
   sage: from lmfdb import db
   sage: db.fq_fields.col_type
   {u'characteristic': u'bigint',
    u'conway': u'smallint',
    u'degree': u'integer',
    u'id': u'bigint',
    u'polynomial': u'jsonb'}
   ```

1. How do I search for entries in a table?

   Use the `search` method on a table.  For example,
   ```python
   sage: from lmfdb import db
   sage: nf = db.nf_fields
   sage: info = {}
   sage: nf.search({'degree':int(6)}, projection=['label','class_number','galt'], limit=4, info=info)
   [{'class_number': 1, 'galt': 5, 'label': u'6.0.9747.1'},
    {'class_number': 1, 'galt': 11, 'label': u'6.0.10051.1'},
    {'class_number': 1, 'galt': 11, 'label': u'6.0.10571.1'},
    {'class_number': 1, 'galt': 5, 'label': u'6.0.10816.1'}]
   sage: info['number'], info['exact_count']
   (5522600, True)
   ```

   The first argument is a dictionary specifying the query (in a style
   similar to what you're used to from MongoDB, but with custom
   operators like `$contains` that are translated to Postgres
   expressions).  You can project in order to obtain only a certain
   set of columns, and provide limits, offsets and custom sort orders.
   Note that if you specify the projection as a string (instead of a
   list), you will get just the values in that column, rather than
   dictionaries.

   The `info` argument is a dictionary that will be updated with
   various data that is commonly needed by templates populated by the
   search functions.  For more details, see the documentation in
   `backend/database.py`.

1. What if I only want a single entry, for example with a specified label?

   Use either the `lucky` method or the `lookup` method.  The first is
   more general, allowing you to specify a query that produces a
   single result (if you're sure it produces only one result,
   specifying `sort=[]` may improve performance).  The `lookup` method
   is a specific case that takes just a label and returns the row with
   that label.

1. What other methods are of interest in querying the database?

   You can use `exists` to determine whether there are any matches for
   a query.

   The `random` method produces a random label or row.

   The `max` method finds the maximum value attained by a specified
   column.

   The `distinct` method returns the distinct values taken by a
   specified column.

   The `count` method returns the total number of rows matching a
   given query.

   The `_parse_projection` method controls how you can specify output
   columns.

   The `_parse_special` method defines the keys that allow more
   complicated queries, such as containment, inequalities and
   disjunctions.

1. How can I execute other kinds of SQL commands?

   You have three options: use the `_execute` method of the `db` object,
   run commands from a `psql` prompt, or use the `pgAdmin4` interface
   (not yet supported).

   If use `db._execute`, make sure to wrap your statements in the SQL
   class from `psycopg2.sql` (you can also import it from
   `lmfdb.backend.database`). You can see lots of examples of this
   paradigm in `lmfdb/backend/database.py`.

   ```python
   sage: from lmfdb.backend.database import db, SQL
   sage: cur = db._execute(SQL("SELECT label, dim, cm_discs, rm_discs from mf_newforms WHERE projective_image = %s AND cm_discs @> %s LIMIT 2"), ['D2', [-19]])
   sage: cur.rowcount
   2
   sage: list(cur)
   [(u'95.1.d.a', 1, [-19, -95], [5]), (u'171.1.c.a', 1, [-3, -19], [57])]
   ```

   If you do this within lmfdb code (rather than just at the command line),
   make sure you properly escpae literals and identifiers to prevent
   SQL injection attacks.  This means wrapping any table or column
   name that might have come from an untrusted source in `Identifier`,
   and using either the %s construction shown above or the `Literal`
   or `Placeholder` objects when passing constants into your query.
   More documentation on these constructions can be found in the
   `psycopg2.sql` module.

   If you want to use SQL from a command prompt, you should log into
   `legendre.mit.edu` (ask Edgar Costa or David Roe if you need an account)
   and then run the following from bash:

   `psql -d lmfdb` and then give the lmfdb password. This will give you
   read-only access to the database.

   If you want write access, type `psql -U editor -d lmfdb` and then give
   the editor password.

   Either way, you will get a prompt where you can type SQL commands.
   Don't forget ending semicolons, which are not required when executing
   commands from python.

Developer configuration
-----------------------

1. Where do I put my passwords?

   When you run `sage -python start-lmfdb.py` for the first time, it
   will create a configuration file `config.ini` in the lmfdb root
   directory.  In the `postgresql` section it will add the default
   username `lmfdb`, password `lmfdb`, host `devmirror.lmfdb.xyz`, and
   port `5432` which altogether allows for read access to the
   database.

   In order to get write access to the database, you need to connect
   to the PostgreSQL server running at `legendre.mit.edu`, which only
   accepts internal connections.  For this we recommend to `ssh` into
   `legendre.mit.edu`, change the `user` field to `editor`, the
   `password` field to the editor password, and the `host` to
   `localhost`.  Instead, if you prefer to work from your own machine,
   you may use the `ssh` connection to forward a local port to `5432`,
   and use that port on your `config.ini` file.

Adding and modifying data
-------------------------

Note that you need editor priviledges to add, delete or modify data.

1. How do I create a new table?

    The following example creates a new postgres table with name
    `test_table` and three columns: `dim` of type `smallint` (a 2-byte
    signed integer), `discriminant` of type `numeric` (an arbitrary
    precision integer/decimal) and `label` of type `text`.  For more
    details see the documentation of the `create_table` function.

    ```python
    sage: from lmfdb import db
    sage: cols = {'smallint': ['dim'], 'numeric': ['discriminant'], 'text': ['label']}
    sage: db.create_table("test_table", cols, label_col="label", sort=['dim', 'discriminant'])
    ```

    Once this table exists, you can access it via the object
    `db.test_table`, which is of type `PostgresTable`.

1. How do I see the type of a column?

    You can access the type of a column using the `col_type`
    attribute.

    ```python
    sage: db.test_table.col_type['dim']
    'integer'
    ```

1. How do I add a column?

   If you want to add a column to an existing table, use the
   `add_column` method.

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

   The second is `copy_from`, which takes a file with one line per row
   to be inserted, with tabs separating the data on each line.  For
   large numbers of rows, this method will be faster.

   ```python
   sage: db.test_table.copy_from('test.txt', sep='|'])
   ```

   Example contents of `test.txt`:

   ```
   dim|discriminant|label|bad_primes
   smallint|numeric|text|jsonb

   1|12|1.12.A|[2,3]
   2|30|2.30.A|[2,3,5]
   ```

   Note that very few (if any) LMFDB tables currently enforce
   uniqueness on any of their columns, so be careful that you do not
   insert duplicate rows.

   You can also export your data using `copy_to`, add rows to the
   resulting file, then use `reload` to load the result back into
   postgres.

1. How do I update data?

   There are a number of methods for updating data.  We present them
   in rough order of ease of use, and roughly reverse order in terms of speed.

   The first option is
   `upsert`, which takes a query and dictionary containing values to
   be set and updates a single row satisfying the query.  If no row
   satisfies the query, a new row will be added.  If multiple rows
   satisfy the query, an error will be raised.  Note that columns
   not contained in the specified data will be left unchanged.

   ```python
   sage: db.test_table.upsert({'discriminant': 12}, {'label':'1.12.B'})
   sage: db.test_table.upsert({'discriminant': 20, 'dim': 2}, {'label':'2.20.B', 'bad_primes':[2,5]})
   ```

   Since upsert only modifies one row at a time, it will be slow if
   many rows need to be changed.  Another option is the `rewrite`
   method.  The first argument is a function that processes an
   existing row and outputs a dictionary giving the changes to be
   made.  The second is an optional query allowing you to filter rows
   from being processed.  Further keywords are documented in the
   docstring for the function.

   ```python
   sage: def func(D):
   ....:     D['dim'] += 1
   ....:     old_label = D['label']
   ....:     D['label'] = str(D['dim']) + old_label[:old_label.find('.')]
   ....:     return D
   sage: db.test_table.rewrite(func, {'discriminant':{'$le':25}})
   ```

   Sometimes the new data cannot be derived from existing data.  In this case
   the `update_from_file` function can be used, which allows you to specify
   new values for any subset of columns and of rows.  For example:

   ```python
   sage: db.test_table.update_from_file("test.txt", label_col="label", sep=":")
   ```

   Example contents of `test.txt`:

   ```
   label:discriminant:bar
   text:numeric:text

   1.12.A:33:hello
   2.30.A:90:world
   ```

   Under the hood, the `rewrite` function uses `reload`, which is
   also available for use directly.  It takes as input files
   containing the desired data for the table (for basic usage, you can
   just give one file; others are available if your table has an
   attached extra table, or you want to update the stats with the same
   command).

   ```python
   sage: db.test_table.reload("test.txt", includes_ids=False)
   ```

   Example contents of `test.txt`:

   ```
   2    12      2.12.B  [2,3]
   3    30      3.30.A  [2,3,5]
   3    20      3.20.B  [2,5]
   ```

   The `reload` method supports arbitrary changes to the data, but requires you to
   produce an appropriate file.

1. What if I change my mind and want to revert to the old version of a table, from before a reload?

   You can use the `reload_revert` method to switch back to the old
   version.  Note that this will also work for the `rewrite` method,
   since it relies on `reload`, and for the `update_from_file` method
   (unless `inplace=True` was used).  If you want to undo a `reload_all`,
   see the `reload_all_revert` method on `db`.

   There is no built-in way to undo direct additions to tables via
   `copy_from`, `upsert`, or `insert_many`.

1. What is an `extra_table`?

   A few large tables (e.g. `nf_fields` and `ec_curves`) have been
   split in two.  The columns in the search table can be used in
   queries, while the columns in the extra table cannot.  Moreover,
   you should refrain from projecting onto columns in the extra table
   in queries that contain more than a few results (in particular,
   queries without a `LIMIT` clause).  The columns in the extra table
   are intended to be accessed by the `lookup` and `lucky` methods
   that only return a single row.

   The benefit of having an extra table is that it drastically shrinks
   the size of the table on which queries are actually being
   performed.  For both elliptic curves and number fields, the search
   table is about a seventh the size of the extra table.  Keeping the
   search table small means that if we need to resort to a sequential
   scan it will be faster.

   If you use the public interface, the distinction between search and
   extra tables should be mostly invisible.  But if you are working
   with a large table it may be worth splitting it in a similar way;
   see the `create_extra_table` method.

1. What should I know about sorting?

   Every search table has an `id` column, which is a 64-bit integer.
   One purpose is to link rows in search tables with corresponding
   rows in the extra table.  Another is to simplify sorting for tables
   that have multiple columns defining their sort order (which is most
   of them).

   Since tables in the LMFDB are updated rarely, and they have a
   standard sort order (based on the order results are displayed on
   the website), it's feasible to have a column that mirrors this sort
   order in integers.  For tables with the `_id_ordered` attribute
   (also stored in the `meta_tables` table), the `id` column serves
   this purpose.  As a consequence, indexes can contain this column,
   rather than all of the columns that define the sort order.  The
   `id` column is added as a primary key, and because its used for
   sorting, many queries will actually use this primary key in
   searches (see the next section on `analyze`).

   The actual sort order for each table is specified at creation time,
   but it can be changed using the `set_sort` method.  The sort order
   is stored in `meta_tables` and in the `_sort` attribute on each
   table, as a string.  It is this default sort order that is used
   when you don't specify a sort in a search query.

   Actually, the `id` column will be used as the sort order (if
   `_id_ordered` is True, `_out_of_order` is False and the query does
   not contain the first column of the true sort order).  This last
   point is important because the query planner does not know that the
   id column is correlated with the columns that define it.

   If the sort order is broken (either by changing the columns that
   define it or by modifying or adding rows), you can use the `resort`
   method to reset it (changing the `id` column to match the correct
   order).  Many of the methods that modify tables include an option
   to `resort` afterward.

1. How do I create a new table?

   If you want to add a new table to the lmfdb, see the `create_table`
   method.  You will need to provide a name (try to follow the naming
   conventions, where the first few characters indicate the general
   area of your table, separated by an underscore from the main name,
   which is often a single word).  You then give a dictionary whose
   keys are postgres types and values are lists of columns with that
   type.  The next argument is the column which should be used in the
   `lookup` method.  You should provide a default sort order if your
   table will be the primary table behind a section of the website
   (auxiliary tables may not need a sort order).  The `id_ordered`
   argument specifies whether the `id` column should match your sort
   order (which can make indexes smaller and simpler but updating data
   more time-consuming).  You can give columns for an extra table (see
   the question two prior), using the same format as the second
   argument.  Finally, you can specify the order of columns, which
   will be used in `copy_from` and `copy_to` by default.

   ```python
   db.create_table(name='halfmf_forms',
                   search_columns={'smallint': ['dim', 'weight', 'level', 'dimtheta'],
                                   'text': ['label'],
                                   'jsonb': ['thetas', 'newpart'],
                                   'numeric': ['character']},
                   label_col='label',
                   sort=['level', 'label'],
                   id_ordered=False,
                   search_order=['dim', 'weight', 'thetas', 'level', 'character',
                                 'label', 'dimtheta', 'newpart'])
   ```

   Conversely, to remove a table from the LMFDB you can use `drop_table`.

1. What other methods should I be aware of for modifying data?

   The `delete` method will delete rows from a table that satisfy a
   given query (if you want to delete all rows, use the empty query
   `{}`).

   The `drop_column` method allows you to drop a column from a table.

Performance and indexes
-----------------------

1. If my queries are running slowly, what can I do about it?

   Once you have a substantial number of rows in your table
   (e.g. hundreds of thousands or more), you will start needing to
   worry about performance.  The main tool we have to improve
   performance is the creation of indexes.

1. How do I create an index, and what types are available?

   In order to create an index on your table, use the `create_index`
   method.  There are two main index types used in the lmfdb (though
   postgres supports others).  The `btree` type is the main one, which
   allows for ordering and searching.  If you want to test set
   containment you can use the `gin` type on a `jsonb` column.  For
   most of our applications we use the `jsonb_path_ops` option (which
   is the default in the lmfdb interface if you specify a `gin`
   index); be aware that it only supports the containment operator
   `@>`, not `<@`.

   If you decide you don't need an index, you can drop it with the
   `drop_index` method.

1. If my queries are still slow, what should I do?

   Use the `analyze` method to determine what query plan postgres is
   choosing.  Sometimes it may not be taking advantage of your index.
   One possible source of problems is the interaction between sort
   orders and `LIMIT` clauses and your search terms.  Another is that
   different columns can be correlated in ways that cause the query
   planner to misestimate the number of results, causing it to choose
   a poor query plan.  The second issue can be alleviated to some
   extent by using Postgres' extended statistics objects, though we
   have not yet done so in the LMFDB.  More details on query
   optimization is beyond the scope of this document; search online or
   ask on the LMFDB mailing list.

Statistics
----------

1. What are statistics used for in the LMFDB?

   One purpose of statistics is to inform viewers of the website of
   the extent of the data.  Many sections of the lmfdb have statistics
   pages for this purpose (e.g. [number field
   statistics](http://www.lmfdb.org/NumberField/stats)).  Each table
   has an attached statistics object (e.g. `db.nf_fields.stats`) with
   methods to support the collection of and access to statistics on
   the table.

   Of course, one of the mathematical aims of the lmfdb is to use
   databases to understand statistical trends in the objects that we
   study.  There is still much that should be done to make statistics
   more sophisticated than counts and averages available for study.

   Another purpose of statistics is to record counts of queries so
   that fewer common queries will result in the "at least 1000
   results" message.  While aggregated statistics such as maximums,
   minimums and averages are stored in tables like `nf_fields_stats`,
   counts of the number of rows with a given set of values taken on by
   specific columns are recorded in tables such as `nf_fields_counts`.

   Finally, statistics are used by the query planner when searching
   for rows.  These statistics are stored internally within postgres
   using postgres' `ANALYZE` and `CREATE STATISTICS` functions, and
   are not easily accesssible to developers.

1. How do I access statistics?

   There are two methods to determine a count of the number of results
   for a given query: `quick_count` (which returns `None` if the query
   is not recorded in the `_counts` table) and `count` (which will
   actually count the number of rows if not recorded, and store the
   answer in the `_counts` table by default).  The `max` method will
   return the maximum value attained by a column.

   In addition, the `display_data` method is designed to provide a
   dictionary for use in creating statistics webpages.  See
   `lmfdb/genus2_curves/main.py` for an example of it in use.  Some
   tables are still using statistics created in Mongo (see
   `create_oldstats` and `get_oldstat`) but they should be
   transitioned to the new statistics functionality in order to more
   easily update.

1. How do I add statistics for a set of columns?

   See the `add_stats` method.  It allows you to specify a set of
   columns, and then will compute counts of the rows with a given set
   of values taken on by those columns.  You can also add a threshold,
   in which case the function will only compute counts of at least the
   threshold.  You can also specify a dictionary of constraints (in
   fact, an arbitrary search query), in which case only rows
   satsifying the query will be considered.

   For example, consider the following data.
   ```
   A B
   1 0
   1 0
   1 1
   2 0
   2 1
   2 2
   2 2
   3 0
   4 1
   5 0
   5 1
   8 2
   ```

   If you added stats for column `A`, it would record that there are
   four instances of 2, three of 1, two of 5 and one each of 3, 4, and
   8.  It would also record the minimum value (1), the maximum value
   (6), the average (3), and the total (12 rows).

   If you specified a threshold of 3, it would only record that there
   are four instances of 2 and three of 1.  Now the minimum and
   maximum values would be 1 and 2 (resp.), the average would be 1.57
   and the total number of rows 7.

   If you instead specified a constraint that B be at most 1, it would
   throw out the rows with B=2, producing three instances of 1, two of
   2, two of 5 and one each of 3 and 4, with the corresponding
   statistics.

   If you want to group values into buckets (for example, class
   numbers of number fields split into ranges like 1 < h <= 10 and 10
   < h <= 100 and 100 < h <= 1000), you can use the
   `add_bucketed_counts` method.

   If you want to add counts for many sets of columns (in order to
   provide counts for common queries that have a large number of
   results), `add_stats_auto` may be useful.

1. How can I easily add a statistics page?

   Create a statistics object inheriting from `StatsDisplay` in
   `lmfdb/display_stats.py`.  It should have attributes

   - `short_summary` (which can be displayed at the top of your browse page), 
   - `summary` (which will be displayed at the top of the statistics page),
   - `table` (the postgres table on which statistics are computed),
   - `baseurl_func` (the function giving your browse page, e.g. `'.index'`),
   - `stat_list` (a list of dictionaries giving the statistics to be displayed; 
   - `'cols'`, `'row_title'` and `'knowl'` are required arguments,
   - and other optional arguments allow you to adjust the default behavior)

   Once you've created such an object, you can call its `setup()`
   method from a sage prompt (with editor privileges) in order to
   collect the relevant statistics.  You should also create a view
   using the `display_stats.html` template, passing your object in as
   the `info` parameter.  Note that `DisplayStats` inherits from
   Sage's `UniqueRepresentation, so it will only be created once.

1. How do I display statistics from multiple tables on one page?

   You can use the `'table'` and `'query_formatter'` keys.  See
   classical modular forms for an example.

1. How do I make dynamic statistics work?

   Once you create a statistics object inheriting from `StatsDisplay`
   and populate it appropriately, enabling dynamic statistics is
   fairly easy.  Just add a view using the `dynamic_stats.html`
   template, and call the `dynamic_setup` method of your stats object
   with `info` as an argument.  See classical modular forms for an
   examaple.

Data Validation
---------------

1. How can I add consistency checks for data in the LMFDB?

   One option is to add constraints to your table.  To do so, use the
   `create_constraint` method in `database.py`.  You can see the
   current constraints using `list_constraints`.

   There are three supported types of constraints.  The simplest is
   `not null`, which checks that a specified column is filled in for
   every row in the table.  The second is `unique`, which checks that
   a column or set of columns is unique across all rows of a table.
   The final options is `check`, which runs an arbitrary SQL function
   on a set of rows.  We are building up a library of SQL functions
   for use in this way; you can see them in `backend/utils.psql`.
   Once written, these functions need to be added to postgres, at
   which point they can be used in checks.

   Note that constraints are checked whenever a row is added or
   updated, so if they are complicated it will impose a speed penalty
   when changing data.

1. What if I do not want to use a constraint, or if I want to add
   checks that cross multiple tables?

   You can use the `lmfdb.verify` module.  Create a python file in the
   `lmfdb/verify` folder with the same name as your postgres table,
   and a class in that file that inherits from `TableChecker` in
   `lmdfb.verify.verification`.  You can then add tests, which should
   be decorated with one of the four speed types imported from
   `lmfdb.verify.verification`.

   The fastest option is to write an SQL query that searches for
   violations of your condition.  The `TableChecker` class has various
   utilities for writing such queries, such as `check_values`,
   `check_iff`, `check_count`.  You can also write the query directly
   and use `_run_query`.  If you want to run queries that check
   consistency accross multiple tables, see the `check_crosstable`
   utility functions.  For fast queries you can use the `@overall`
   decorator; if your query takes longer than about a minute, you may
   want to use the `@overall_long` decorator instead.

   `@fast` and `@slow` tests are run by iterating over rows in the
   table.  They take a dictionary representing a row as input, and
   should return either True (if the test passes) or False.  You can
   provide keyword arguments to the decorator: `ratio` controls the
   fraction of rows in your table on which the test is run,
   `projection` controls which columns of the table are present in the
   record, and `constraint` provides a constraint on rows on which the
   test is run.  The difference between fast and slow tests is just a
   matter of convention: fast tests are run by default on every row of
   the table and should take about a minute each to run, while slow
   tests are run by default on 10% of the rows of a table and can take
   longer.

   You must run verification tests manually from a Sage prompt.
   First, run `from lmfdb.verify import db`.  This will give you a
   version of the database with verification enabled (it is not
   enabled by default since the verification checks are vulnerable to
   SQL injection and should not be available when the website is
   running).  Then use, for example, `db.mf_newforms.verify()`.

   You can specify a paricular speedtype to run
   (e.g. `speedtype="slow"` or `speedtype="overall"`), a specific
   check (e.g. `check="check_cmrm_discs"`), or a specific object (e.g.
   `label="24.37.h.c"`).  You can also run tests on multiple tables
   in parallel using `db.verify()`.

   The tests will write output to a log folder (defaulting to
   `LMFDB_ROOT/logs/verification`), and will also print the output
   sent to this folder to your terminal.  You can control which output
   you see using the `follow` option.

1. How can I see what verification functions are written for a given table?

   You can use the `list_verifications()` method.  With
   `details=False` it will show a list of verification functions; if
   `details=True` it will also print their docstrings and
   configuration options that differ from the defaults.

SQL Tips
--------

Sometimes the interface isn't enough, and you need to do something directly with SQL.
Note that some of these operations will require you to be logged in as editor.

1. How can I change the type of a column from jsonb to an array?

   When we first switched to postgres, we planned to use jsonb for
   everything.  But we have since learned that there are some
   advantages to using Postgres arrays.  If you want to convert from
   jsonb to an array (of numerics) for example, you could do the
   following.  We first check to see if this column is being used in
   any indexes or constraints.  If it were, you would need to update
   `meta_indexes` or `meta_constraints`.

   ```
   lmfdb=> SELECT * FROM meta_indexes WHERE columns @> '["heights"]'::jsonb;
    index_name | table_name | type | columns | modifiers | storage_params
   ------------+------------+------+---------+-----------+----------------
   (0 rows)
   lmfdb=> SELECT * FROM meta_constraints WHERE columns @> '["heights"]'::jsonb;
    constraint_name | table_name | type | columns | check_func
   -----------------+------------+------+---------+------------
   (0 rows)
   lmfdb=> ALTER TABLE ec_nfcurves ADD COLUMN new_heights numeric[];
   ALTER TABLE
   lmfdb=> SELECT label, heights, (SELECT array_agg(value::numeric) FROM jsonb_array_elements_text(heights)) AS new_heights FROM ec_nfcurves WHERE jsonb_array_len(heights) > 1 LIMIT 3;
           label        |                  heights                  |               new_heights
   ---------------------+-------------------------------------------+------------------------------------------
    2.2.8.1-2066.2-e1   | [0.2026108605260589, 0.1517386576969303]  | {0.2026108605260589,0.1517386576969303}
    3.1.23.1-15857.3-A2 | [0.06782294138768774, 0.6525410927449266] | {0.06782294138768774,0.6525410927449266}
    3.1.23.1-18509.3-A1 | [0.1658028623327324, 0.2297502250210176]  | {0.1658028623327324,0.2297502250210176}
   (3 rows)
   lmfdb=> UPDATE ec_nfcurves SET new_heights = (SELECT array_agg(value::numeric) FROM jsonb_array_elements_text(heights));
   UPDATE 661073
   lmfdb=> ALTER TABLE ec_nfcurves RENAME COLUMN heights TO old_heights;
   ALTER TABLE
   lmfdb=> ALTER TABLE ec_nfcurves RENAME COLUMN new_heights TO heights;
   ALTER TABLE
   ```
