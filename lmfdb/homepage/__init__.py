import yaml

from lmfdb.config import lmfdb_package_dir
from .boxes import load_boxes
from .sidebar import get_sidebar

# reading and sorting list of contributors once at startup
with open(lmfdb_package_dir / "CONTRIBUTORS.yaml") as contrib_file:
    contribs = yaml.load_all(contrib_file, Loader=yaml.FullLoader)
    contribs = sorted(contribs, key=lambda x: x['name'].split()[-1])

__all__ = ['load_boxes', 'contribs', 'get_sidebar']
