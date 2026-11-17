"""
A thin client for Zenodo's deposit REST API (create deposition, upload files
to the bucket, publish, new version), with retry/backoff and a hard safety:
a client constructed without ``live=True`` raises ``NotLive`` on *any*
network access, so nothing in the backup system can touch Zenodo (or the
sandbox) unless explicitly enabled.

Tokens need the ``deposit:write`` and ``deposit:actions`` scopes.
"""

import os
import time

from .packaging import hash_file


class ZenodoError(RuntimeError):
    pass


class NotLive(ZenodoError):
    """Raised when a non-live client is asked to perform a network request."""


class NotFound(ZenodoError):
    """The deposition or record does not exist (e.g. a discarded draft)."""


class QuotaExceeded(ZenodoError):
    """The draft needs more than the available quota (owner must raise it
    via the record's "Manage storage" button in the Zenodo UI)."""


PROD_API = "https://zenodo.org/api"
SANDBOX_API = "https://sandbox.zenodo.org/api"

# Zenodo's stated defaults: 50GB and 100 files per record.
DEFAULT_QUOTA = 50 * 10**9
MAX_FILES = 100


class ZenodoClient:
    def __init__(self, token, sandbox=False, live=False, log=print,
                 min_interval=0.7, max_retries=6):
        """
        - ``token`` -- a personal access token of the record's owner
        - ``sandbox`` -- use sandbox.zenodo.org (separate tokens!)
        - ``live`` -- unless True, any network access raises ``NotLive``
        """
        self.token = token
        self.sandbox = sandbox
        self.live = live
        self.log = log
        self.base = SANDBOX_API if sandbox else PROD_API
        self.min_interval = min_interval
        self.max_retries = max_retries
        self._last_request = 0.0
        self._session = None

    def _request(self, method, path, desc, **kwds):
        """
        Perform one API request (with retry/backoff on 429/5xx), returning
        the parsed JSON.  ``path`` may be a full URL (bucket links) or a
        path relative to the API base.
        """
        if not self.live:
            raise NotLive(
                "refusing %s %s (%s): client is not live.  Construct "
                "ZenodoClient(..., live=True) once uploads are approved."
                % (method, path, desc))
        import requests
        if self._session is None:
            self._session = requests.Session()
        url = path if path.startswith("http") else self.base + path
        headers = kwds.pop("headers", {})
        headers["Authorization"] = "Bearer %s" % self.token
        # a failed attempt may have consumed a streamed upload body
        body = kwds.get("data")
        start = body.tell() if hasattr(body, "seek") else None
        for attempt in range(self.max_retries):
            if start is not None:
                body.seek(start)
            wait = self.min_interval - (time.time() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.time()
            resp = self._session.request(method, url, headers=headers,
                                         timeout=(30, 600), **kwds)
            if resp.status_code in (429, 500, 502, 503, 504):
                delay = resp.headers.get("Retry-After")
                delay = int(delay) if delay and delay.isdigit() else 2 ** attempt
                self.log("Zenodo %s on %s; retrying in %ss"
                         % (resp.status_code, desc, delay))
                time.sleep(delay)
                continue
            break
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text[:500]
            # Zenodo answers an upload beyond the record's remaining quota
            # with 400 "File size limit exceeded." (its per-file limit gives
            # the same message, but our parts stay below it)
            text = str(detail).lower()
            if (resp.status_code == 413 or "quota" in text
                    or "size limit exceeded" in text):
                raise QuotaExceeded("%s: %s %s" % (desc, resp.status_code, detail))
            if resp.status_code in (404, 410):
                raise NotFound("%s: %s %s" % (desc, resp.status_code, detail))
            raise ZenodoError("%s failed: %s %s" % (desc, resp.status_code, detail))
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # Depositions ####################################################

    def create_deposition(self, metadata=None):
        """Create a new deposition (draft); returns its JSON (with
        ``links.bucket`` and a prereserved DOI)."""
        return self._request("POST", "/deposit/depositions",
                             "create deposition", json=metadata or {})

    def get_deposition(self, dep_id):
        return self._request("GET", "/deposit/depositions/%s" % dep_id,
                             "get deposition %s" % dep_id)

    def update_metadata(self, dep_id, metadata):
        return self._request("PUT", "/deposit/depositions/%s" % dep_id,
                             "update metadata of %s" % dep_id, json=metadata)

    def delete_draft(self, dep_id):
        """Discard an unpublished draft (published records cannot be
        deleted)."""
        return self._request("DELETE", "/deposit/depositions/%s" % dep_id,
                             "discard draft %s" % dep_id)

    def publish(self, dep_id):
        return self._request("POST",
                             "/deposit/depositions/%s/actions/publish" % dep_id,
                             "publish %s" % dep_id)

    def new_version(self, dep_id):
        """
        Create (or fetch, if one is already open) the draft for a new version
        of a published record; returns the draft deposition JSON.  Files are
        inherited from the previous version: delete the changed ones and
        upload replacements, leaving unchanged files to Zenodo's
        deduplication.
        """
        dep = self._request(
            "POST", "/deposit/depositions/%s/actions/newversion" % dep_id,
            "new version of %s" % dep_id)
        draft = dep.get("links", {}).get("latest_draft")
        if not draft:
            raise ZenodoError("no latest_draft link on %s" % dep_id)
        return self._request("GET", draft, "get draft of %s" % dep_id)

    # Files ##########################################################

    def list_files(self, dep_id):
        return self._request("GET", "/deposit/depositions/%s/files" % dep_id,
                             "list files of %s" % dep_id)

    def upload_file(self, bucket_url, path, name=None, verify=True):
        """
        Streamed PUT of ``path`` into the deposition's bucket.  If ``verify``,
        compare Zenodo's reported md5 against the local file and raise on
        mismatch.  Returns the file JSON.
        """
        name = name or os.path.basename(str(path))
        size = os.path.getsize(path)
        self.log("Uploading %s (%.2f GB)" % (name, size / 1e9))
        with open(path, "rb") as F:
            info = self._request("PUT", "%s/%s" % (bucket_url, name),
                                 "upload %s" % name, data=F)
        if verify:
            remote = info.get("checksum", "")
            local = "md5:" + hash_file(path, count_lines=False)[1]
            if remote and remote != local:
                raise ZenodoError("checksum mismatch for %s: %s (zenodo) "
                                  "!= %s (local)" % (name, remote, local))
        return info

    def delete_file(self, file_link):
        return self._request("DELETE", file_link, "delete file")

    # Published records (read-only) ##################################

    def get_record(self, recid):
        return self._request("GET", "/records/%s" % recid,
                             "get record %s" % recid)

    def verify_record(self, recid, local_md5s):
        """
        Compare a published record's file checksums against
        ``{filename: md5}``; returns a list of mismatch/missing messages
        (empty = verified).
        """
        record = self.get_record(recid)
        remote = {f["key"]: f.get("checksum", "")
                  for f in record.get("files", [])}
        problems = []
        for name, md5 in local_md5s.items():
            if name not in remote:
                problems.append("%s missing on Zenodo" % name)
            elif remote[name] not in ("md5:" + md5, md5):
                problems.append("%s: %s (zenodo) != md5:%s (local)"
                                % (name, remote[name], md5))
        return problems
