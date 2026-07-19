# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2010-2012 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

"""
The configuration code now lives in lmfdb/config.py, so that using the
database does not require importing lmfdb.utils (and its dependencies);
this module remains for backwards compatibility.
"""

if __name__ == "__main__":
    # Support running this file as a script (as the CI does to write a
    # config file) by adding the repository root to sys.path
    import os
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from lmfdb.config import (
    Configuration,
    ConfigWrapper,
    find_config_file,
    get_secret_key,
    is_port_open,
    lmfdb_home,
    lmfdb_log_dir,
    root_lmfdb_path,
)

__all__ = [
    "Configuration",
    "ConfigWrapper",
    "find_config_file",
    "get_secret_key",
    "is_port_open",
    "lmfdb_home",
    "lmfdb_log_dir",
    "root_lmfdb_path",
]

if __name__ == "__main__":
    Configuration(writeargstofile=True, readargs=True)
