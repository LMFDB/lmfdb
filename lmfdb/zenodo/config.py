"""
Machine-local configuration for the Zenodo backup system.

This is deliberately independent of the LMFDB's main configuration mechanism
(which is being reworked for pip-installability): the settings here include
personal API tokens and only exist on the machines running backups (proddb),
in a file that should be owned by the account running the pipeline with mode
0600.

Default location ``~/.lmfdb_zenodo.ini``, overridden by the
``LMFDB_ZENODO_CONFIG`` environment variable.  Format:

    [zenodo]
    # nothing is uploaded unless enabled is true AND callers pass live=True
    enabled = false
    sandbox = true
    community = lmfdb
    staging_dir = /scratch/zenodo
    chunk_gb = 20
    compression_level = 12
    # editor recorded in version_history / userdb.zenodo_backups
    editor = roed
    # owner of new records when tables.yaml does not assign one
    default_owner = roed

    [tokens]
    roed = <personal access token>
    someone_else = <their token>
"""

import configparser
import os
import stat


DEFAULT_PATH = os.path.expanduser("~/.lmfdb_zenodo.ini")


class ZenodoConfig:
    def __init__(self, path=None):
        self.path = os.path.expanduser(
            path or os.environ.get("LMFDB_ZENODO_CONFIG", DEFAULT_PATH))
        self.exists = os.path.exists(self.path)
        parser = configparser.ConfigParser()
        if self.exists:
            mode = stat.S_IMODE(os.stat(self.path).st_mode)
            if mode & 0o077:
                print("WARNING: %s is readable by others (mode %o); "
                      "it contains API tokens and should be chmod 600"
                      % (self.path, mode))
            parser.read(self.path)
        z = parser["zenodo"] if parser.has_section("zenodo") else {}
        self.enabled = str(z.get("enabled", "false")).lower() == "true"
        self.sandbox = str(z.get("sandbox", "true")).lower() == "true"
        self.community = z.get("community", "lmfdb")
        self.staging_dir = z.get("staging_dir", "/scratch/zenodo")
        self.chunk_gb = float(z.get("chunk_gb", 20))
        self.compression_level = int(z.get("compression_level", 12))
        self.editor = z.get("editor") or None
        self.default_owner = z.get("default_owner") or None
        self.tokens = dict(parser["tokens"]) if parser.has_section("tokens") else {}

    def token_for(self, owner):
        if owner not in self.tokens:
            raise ValueError(
                "no Zenodo token for %r in %s (owners with tokens: %s)"
                % (owner, self.path, ", ".join(sorted(self.tokens)) or "none"))
        return self.tokens[owner]
