
# psycodict was added as a dependency on May 10, 2024; we provide a useful error message for people upgrading
try:
    import psycodict
    assert psycodict
except ImportError:
    print('Missing dependency; try running "sage -pip install -r requirements.txt" in the LMFDB home folder.')
    raise

from .lmfdb_database import db
assert db
