"""
Utilities for websites like the L-functions and modular forms database
(https://www.lmfdb.org): search forms and their parsing, search results and
downloads, statistics pages, and displaying mathematical objects.

Import what you need from the submodules (``lmfdb_utils.search_wrapper``,
``lmfdb_utils.search_parsing``, ...).  A website using them describes
itself with :mod:`lmfdb_utils.site`.

Most of the modules require flask and SageMath; this package itself (and
:mod:`lmfdb_utils.site`) imports neither.
"""

__version__ = "0.1.0"
