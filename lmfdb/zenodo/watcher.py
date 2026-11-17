"""
Frontend code versions: each push to the ``web`` branch (which the web
servers pull on a cron) gets the next ``code`` number in ``version_history``.
MAJOR is read from ``lmfdb/version.py`` at the pushed commit, so a major
version bump is just an ordinary pull request editing that file.

This normally runs in the GitHub Action ``.github/workflows/code-version.yml``
on every push to ``web``, which copies this directory out of the checkout and
runs

    python -m zenodo.watcher --commit SHA --version-file .../lmfdb/version.py

connecting with the DSN in ``$LMFDB_VERSION_DSN``.  The copy imports this
package on its own: importing ``lmfdb`` itself needs sage and connects to the
configured database.

Without ``--commit`` it polls the head of ``web`` with ``git ls-remote`` and
uses the configured LMFDB database; run ``python3 -m lmfdb.zenodo.watcher``
that way on proddb to catch up after a failed workflow run.

Nothing here talks to Zenodo.
"""

import os
import re
import subprocess

REPO = "https://github.com/LMFDB/lmfdb.git"
RAW_VERSION_FILE = "https://raw.githubusercontent.com/LMFDB/lmfdb/%s/lmfdb/version.py"
BRANCH = "web"
MAJOR_RE = re.compile(r"^MAJOR\s*=\s*(\d+)", re.MULTILINE)


def deployed_commit(repo=REPO, branch=BRANCH):
    """The commit hash at the head of the deployed branch on GitHub."""
    out = subprocess.run(["git", "ls-remote", repo, "refs/heads/" + branch],
                         capture_output=True, text=True, timeout=60, check=True)
    line = out.stdout.strip()
    if not line:
        raise RuntimeError("branch %s not found on %s" % (branch, repo))
    return line.split()[0]


def major_at_commit(commit, current_major):
    """
    MAJOR as declared in lmfdb/version.py at the given commit, or
    ``current_major`` for commits predating the versioning system (no such
    file).  Any other failure to read it raises, so that the commit is not
    recorded under a guessed major version.
    """
    import requests
    resp = requests.get(RAW_VERSION_FILE % commit, timeout=60)
    if resp.status_code == 404:
        return current_major
    resp.raise_for_status()
    m = MAJOR_RE.search(resp.text)
    if not m:
        raise ValueError("no MAJOR in lmfdb/version.py at %s" % commit)
    return int(m.group(1))


def major_from_file(path):
    """MAJOR as declared in a checked-out lmfdb/version.py."""
    with open(path) as F:
        m = MAJOR_RE.search(F.read())
    if not m:
        raise ValueError("no MAJOR in %s" % path)
    return int(m.group(1))


_CONFLICT = object()


def record_deploy(db, commit, major=None, config=None, dry_run=False,
                  observe=None, tries=5):
    """
    Record ``commit``, just pushed to the web branch, as the next code
    version (or as a major version bump if ``major`` exceeds the current
    one).  Commits that already have a code version are skipped, so re-runs
    are harmless.  Returns the new version event as a dict, or None.

    - ``major`` -- MAJOR at ``commit``; fetched from GitHub when None
    - ``config`` -- anything with an ``editor`` attribute (default: the
      local Zenodo configuration)
    - ``observe`` -- returns the current head of the web branch.  When given,
      a commit that is no longer the head is not recorded (numbering it now
      would place it after the newer deploy), and if another deploy is
      recorded between observing the head and numbering, the head is
      observed again (up to ``tries`` times, then RuntimeError)
    """
    from . import state
    from .config import ZenodoConfig

    cfg = config or ZenodoConfig()
    editor = cfg.editor or "deploy-watcher"
    for _ in range(tries):
        current = state.latest_versions(db)
        if current is None:
            raise RuntimeError(
                "version history is empty; run db.zenodo_setup() first")
        seen = state.latest_deploy_id(db) if observe else None
        if state.code_rows_for_commit(db, commit):
            print("Commit %s already has a code version" % commit[:12])
            return None
        if observe is not None:
            head = observe()
            if head != commit:
                print("Commit %s is no longer the head of web (now %s); not "
                      "recorded" % (commit[:12], head[:12]))
                return None
        if major is None:
            major = major_at_commit(commit, current["major"])
        # numbered under the lock that data pushes take to number theirs
        with state.history_lock(db):
            event = _record(db, commit, major, editor, dry_run, seen)
        if event is not _CONFLICT:
            return event
        print("Another deploy was recorded while %s was being checked; "
              "checking the head again" % commit[:12])
    raise RuntimeError("could not record %s: other deploys were recorded "
                       "during each of %s attempts; re-run" % (commit, tries))


def _record(db, commit, major, editor, dry_run, seen=None):
    from . import state
    # again, now that no other recorder can be between check and insert
    if state.code_rows_for_commit(db, commit):
        print("Commit %s already has a code version" % commit[:12])
        return None
    if seen is not None and state.latest_deploy_id(db) != seen:
        return _CONFLICT
    current = state.latest_versions(db)
    if major > current["major"]:
        event = {"kind": "major", "major": major, "seq": 0, "git_hash": commit}
        rows = state.major_rows(major, git_hash=commit, editor=editor)
        if not dry_run:
            state.insert_version_rows(db, rows)
        print("Recorded major version bump to %s.0-0 (commit %s)%s"
              % (major, commit[:12], " [dry run]" if dry_run else ""))
    else:
        seq = current["code_seq"] + 1 if major == current["major"] else 0
        event = {"kind": "code", "major": major, "seq": seq, "git_hash": commit}
        rows = [state.version_row(major, "code", seq, git_hash=commit,
                                  editor=editor)]
        if not dry_run:
            state.insert_version_rows(db, rows)
        print("Recorded frontend release %s.*-%s (commit %s)%s"
              % (major, seq, commit[:12],
                 " [dry run]" if dry_run else ""))
    return event


def check_deploy(db, config=None, dry_run=False, repo=REPO, branch=BRANCH):
    """Record the current head of the deployed branch (see ``record_deploy``)."""
    return record_deploy(db, deployed_commit(repo, branch), config=config,
                         dry_run=dry_run,
                         observe=lambda: deployed_commit(repo, branch))


class _Connection:
    """The part of psycodict's database interface that ``state`` uses."""

    def __init__(self, conn):
        self.conn = conn

    def _execute(self, query, values=None):
        cur = self.conn.cursor()
        cur.execute(query, values)
        return cur


def main():
    import argparse
    from types import SimpleNamespace
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="report without writing to the database")
    parser.add_argument("--branch", default=BRANCH)
    parser.add_argument("--commit",
                        help="the pushed commit; connect using $LMFDB_VERSION_DSN")
    parser.add_argument("--version-file",
                        help="lmfdb/version.py as of --commit")
    args = parser.parse_args()
    if args.commit is None:
        from lmfdb import db
        check_deploy(db, dry_run=args.dry_run, branch=args.branch)
        return
    # SQL objects in state come from psycodict, so connect with its driver
    import psycopg
    major = major_from_file(args.version_file) if args.version_file else None
    cfg = SimpleNamespace(editor="github-actions")
    with psycopg.connect(os.environ["LMFDB_VERSION_DSN"],
                         autocommit=True) as conn:
        record_deploy(_Connection(conn), args.commit, major=major, config=cfg,
                      dry_run=args.dry_run,
                      observe=lambda: deployed_commit(branch=args.branch))


if __name__ == "__main__":
    main()
