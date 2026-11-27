"""
Serving large files from beta.lmfdb.org.
"""
from io import BytesIO
from urllib.parse import urlparse, urlunparse

from flask import redirect, request, send_file


def redirect_to_beta():
    """
    Return a redirect to the current URL on beta.lmfdb.org, or None when already running there.

    Large data files are served from beta: www.lmfdb.org runs on Google Cloud, which charges for every GB it sends, while beta runs at MIT.
    """
    urlparts = urlparse(request.url)
    if urlparts.netloc != "beta.lmfdb.org":
        replaced = urlparts._replace(netloc="beta.lmfdb.org", scheme="https")
        return redirect(urlunparse(replaced), code=301)
    return None

def send_file_from_beta(filepath, line_matcher, **kwds):
    """
    If running on beta.lmfdb.org, return the file as an attachment (potentially filtering lines).  Otherwise, return a redirect to the current URL on beta.
    """
    moved = redirect_to_beta()
    if moved is not None:
        return moved
    if line_matcher is None:
        return send_file(filepath, **kwds)
    bIO = BytesIO()
    with open(filepath) as F:
        for i, line in enumerate(F):
            if line_matcher(i, line):
                bIO.write(line.encode('utf-8'))
    bIO.seek(0)
    return send_file(bIO, **kwds)
