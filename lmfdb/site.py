"""
How the LMFDB describes itself to lmfdb-utils (see lmfdb_utils.site).

Importing the lmfdb package installs :class:`LMFDBSite`, so this module must
stay as light as lmfdb/__init__.py: everything else is imported when used.
"""

from lmfdb_utils.site import Site


class LMFDBSite(Site):
    name = "LMFDB"
    download_prefix = "lmfdb"

    def knowl_title(self, kid):
        from lmfdb.knowledge.knowl import knowl_title
        return knowl_title(kid)

    def knowl_url(self, kid):
        from flask import url_for
        return url_for("knowledge.show", ID=kid)

    def knowl_create_url(self, kid):
        from flask import url_for
        from flask_login import current_user
        from lmfdb.users.pwdmanager import userdb
        if current_user.is_authenticated and userdb.can_read_write_userdb():
            return url_for("knowledge.edit", ID=kid)

    def all_knowls(self):
        from lmfdb.knowledge.knowl import knowldb
        return {rec["id"]: (rec["title"], rec["content"]) for rec in knowldb.get_all_knowls(fields=["id", "title", "content"])}

    def source_url(self, filename):
        from lmfdb.app import is_beta, is_debug_mode, _url_source
        if is_debug_mode():
            branch = "main"
        elif is_beta():
            branch = "dev"
        else:
            branch = "web"
        return "%s%s/%s" % (_url_source, branch, filename)

    def results_complete(self, table, query, db, search_array=None):
        from lmfdb.utils.completeness import results_complete
        return results_complete(table, query, db, search_array)

    def query_timeout_message(self):
        from urllib.parse import urlparse
        from flask import request
        from lmfdb.app import ctx_proc_userdata
        ctx = ctx_proc_userdata()
        if urlparse(request.url).netloc == "beta.lmfdb.org":
            return (
                'The search query took longer than expected! Please try again later; if your search still times out, please help us improve by reporting this error <a href="%s" target=_blank>here</a>.'
                % ctx["feedbackpage"]
            )
        beta_link = ctx["modify_url"](scheme="https", netloc="beta.lmfdb.org")
        return (
            'The search query took longer than expected! The <a href="%s">same search</a> on beta.lmfdb.org may succeed (it is running on a server with faster disks).  You can also try again later; if your search still times out, please help us improve by reporting this error  <a href="%s" target=_blank>here</a>.'
            % (beta_link, ctx["feedbackpage"])
        )
