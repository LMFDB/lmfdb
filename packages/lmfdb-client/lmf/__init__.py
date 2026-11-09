"""
The import name used by lmfdb-lite, which lmfdb-client replaces:
``from lmf import db`` keeps working, and is the same object as
``lmfdb_client.db``.
"""

from lmfdb_client import db

__all__ = ["db"]
