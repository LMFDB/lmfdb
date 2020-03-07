from __future__ import absolute_import
from lmfdb.logger import make_logger
typed_data_logger = make_logger("typed_data_logger", hl=True)

from . import type_generation
assert type_generation
from . import standard_types
assert standard_types
import artin_types
assert artin_types
