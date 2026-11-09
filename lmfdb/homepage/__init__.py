import os
import yaml

from lmfdb.config import root_lmfdb_path
from .boxes import load_boxes
from .sidebar import get_sidebar

# reading and sorting list of contributors once at startup
with open(os.path.join(root_lmfdb_path, "CONTRIBUTORS.yaml")) as contrib_file:
    contribs = yaml.load_all(contrib_file, Loader=yaml.FullLoader)
    contribs = sorted(contribs, key=lambda x: x['name'].split()[-1])

__all__ = ['load_boxes', 'contribs', 'get_sidebar']
