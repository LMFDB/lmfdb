"""
What lmfdb_utils needs to know about the website using it.

A few utilities depend on things that only the website can provide: its
name, its knowls, which results it knows to be complete, and so on.  A
website describes itself by subclassing :class:`Site` and installing an
instance with :func:`set_current_site` when it starts, before handling
requests; the defaults describe a site without knowls.

For example, the LMFDB installs ``lmfdb.site.LMFDBSite`` when the ``lmfdb``
package is imported.

This module must stay importable without flask or sage.
"""


class Site:
    #: The name of the website, as it appears in text such as "downloaded
    #: from the LMFDB" (following "the")
    name = "database"

    #: The prefix of the names of downloaded files
    download_prefix = "download"

    def knowl_title(self, kid):
        """
        The title of the knowl with id ``kid``, or None if there is no such
        knowl.
        """
        return None

    def knowl_url(self, kid):
        """
        The path, on this website, of the page showing the knowl ``kid``
        (used in downloaded spreadsheets), or None.
        """
        return None

    def knowl_create_url(self, kid):
        """
        The address of the page creating the missing knowl ``kid``, if the
        current user may create it, and None otherwise.
        """
        return None

    def all_knowls(self):
        """
        A dictionary giving the title and content of every knowl, by id
        (used to describe the columns in downloaded files).
        """
        return {}

    def source_url(self, filename):
        """
        The address of the file ``filename`` in the website's source code
        repository (used by
        :func:`~lmfdb_utils.utilities.code_snippet_knowl`), or None.
        """
        return None

    def results_complete(self, table, query, db, search_array=None):
        """
        Whether the database contains all objects satisfying a query.

        INPUT:

        - ``table`` -- string, the name of the table
        - ``query`` -- dictionary, the psycodict query
        - ``db`` -- the database
        - ``search_array`` -- the search array of the search, or None

        OUTPUT:

        A triple ``(complete, reason, caveat)``: ``complete`` is True if
        every object satisfying the query is included in the results, False
        if objects may be missing, and None if unknown; ``reason`` is a
        string that can follow "The <name> contains all" when ``complete``;
        ``caveat`` is a string qualifying the answer, or None.
        """
        return None, None, None

    def query_timeout_message(self):
        """
        The message (HTML) shown when a search takes too long and is
        cancelled.
        """
        return "The search query took longer than expected!  Please try again later."


_current_site = Site()


def current_site():
    """
    The :class:`Site` installed with :func:`set_current_site` (by default,
    one describing a site without knowls).
    """
    return _current_site


def set_current_site(site):
    """
    Install ``site``, an instance of a subclass of :class:`Site`, as the
    website using these utilities.
    """
    global _current_site
    _current_site = site
