# lmfdb-utils

Utilities for running a website like the [L-functions and modular forms database](https://www.lmfdb.org) (LMFDB): a [Flask](https://flask.palletsprojects.com) site presenting mathematical objects stored in a PostgreSQL database accessed through [psycodict](https://github.com/roed314/psycodict).  This package is built from the [LMFDB repository](https://github.com/LMFDB/lmfdb), where the LMFDB website uses it, so other websites share the LMFDB's code rather than copies of it.

## Install

Most of the modules require [SageMath](https://www.sagemath.org), which pip cannot install, so install this package into Sage's Python:

```
sage -pip install lmfdb-utils
```

## Contents

- `search_boxes`: the boxes of search forms (`SearchArray`, `TextBox`, `SelectBox`, ...) and the sorting and column controls;
- `search_parsing`: parsing what users type into search boxes into psycodict queries (`parse_ints`, `parse_floats`, `parse_bracketed_posints`, ..., and the `search_parser` decorator for writing new parsers);
- `search_wrapper`: `search_wrap`, `count_wrap`, `embed_wrap` and `yield_wrap`, which turn a function filling in a query into a search results page (with pagination, sorting, random results, downloads and diagram views);
- `search_columns`: the columns of search results tables, and how they are displayed and downloaded;
- `downloader`: `Downloader`, for downloading search results and single objects in Sage, Magma, Pari/GP, GAP, Oscar, CSV and text formats;
- `display_stats`: `StatsDisplay`, for statistics pages built from psycodict's statistics tables;
- `web_display` and `utilities`: displaying mathematical objects (`web_latex`, `raw_typeset`, `bigint_knowl`, `display_knowl`, ...), flashing messages (`flash_error`, ...), pagination and other helpers;
- `color`: the color schemes of the LMFDB's style sheets;
- `place_code`: `CodeSnippet`, for showing code in several computer algebra systems;
- `csrf`, `random_wrap`, `datetime_utils`, `common_regex`: small helpers.

## Describing your website

A few utilities depend on things only the website can provide: its name, its knowls (the LMFDB's short definitions that pop up when clicked), whether search results are known to be complete, and so on.  A website describes itself by subclassing `lmfdb_utils.site.Site` and installing an instance when it starts:

```python
from lmfdb_utils.site import Site, set_current_site

class MySite(Site):
    name = "Diophantine Library"  # as in "downloaded from the Diophantine Library"
    download_prefix = "dl"

    def knowl_title(self, kid):
        ...  # the title of the knowl kid, or None if there is none

set_current_site(MySite())
```

See the docstrings in `lmfdb_utils/site.py` for the other methods, and `lmfdb/site.py` in the LMFDB repository for the LMFDB's implementation.  The defaults describe a site without knowls.

## What is not here yet

The templates and static files that these utilities use are still in the LMFDB repository: `search_wrap` and `StatsDisplay` render `search_results.html`, `display_stats.html`, `d3_diagram.html` and the templates they include (from `lmfdb/templates`), which use the style sheets and scripts in `lmfdb/static` and the knowl system in `lmfdb/knowledge`.  A website using lmfdb-utils currently provides its own copies.

## Development

This package lives in `packages/lmfdb-utils` in the [LMFDB repository](https://github.com/LMFDB/lmfdb); an LMFDB checkout installs it in editable mode (`sage -pip install -r requirements.txt`).  Its modules must not import anything from the `lmfdb` package: what they need from the website goes through `lmfdb_utils.site`.  The tests in `packages/lmfdb-utils/tests` check this, and the LMFDB's own test suite exercises the utilities through the website.
