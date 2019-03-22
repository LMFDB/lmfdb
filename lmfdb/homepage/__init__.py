# -*- coding: utf-8 -*-

import os

import yaml

from .boxes import load_boxes
from .sidebar import get_sidebar

# reading and sorting list of contributors once at startup
_curdir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_curdir, "..", "..", "CONTRIBUTORS.yaml")) as contrib_file:
    contribs = yaml.load_all(contrib_file)
    contribs = sorted(contribs, key = lambda x : x['name'].split()[-1])

__all__ = ['load_boxes', 'contribs', 'get_sidebar']
