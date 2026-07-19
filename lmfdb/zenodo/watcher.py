"""
The deploy watcher: assigns frontend code versions with no change to anyone's
release workflow.

Deploying the LMFDB website means pushing to the ``web`` branch on GitHub
(the web servers pull it on a cron).  This script, run from cron on proddb,
polls the public head of that branch with ``git ls-remote``; when it changes
it records a new ``code`` row in ``version_history`` (bumping the letter
code), reading MAJOR out of ``lmfdb/version.py`` at the deployed commit so
that major version bumps are also detected -- a major bump is therefore just
an ordinary pull request editing that file.

Suggested crontab entry (as the account holding editor credentials):

    */15 * * * * python3 -m lmfdb.zenodo.watcher >> ~/logs/version_watcher.log 2>&1

Requires network access to github.com only; nothing here talks to Zenodo.
"""

import re
import subprocess

REPO = "https://github.com/LMFDB/lmfdb.git"
RAW_VERSION_FILE = "https://raw.githubusercontent.com/LMFDB/lmfdb/%s/lmfdb/version.py"
BRANCH = "web"


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
    MAJOR as declared in lmfdb/version.py at the given commit; falls back to
    ``current_major`` when the file does not exist there (commits predating
    the versioning system) or cannot be fetched.
    """
    import requests
    try:
        resp = requests.get(RAW_VERSION_FILE % commit, timeout=60)
        if resp.status_code == 200:
            m = re.search(r"^MAJOR\s*=\s*(\d+)", resp.text, re.MULTILINE)
            if m:
                return int(m.group(1))
    except Exception as err:
        print("WARNING: could not read version.py at %s: %s" % (commit, err))
    return current_major


def check_deploy(db, config=None, dry_run=False, repo=REPO, branch=BRANCH):
    """
    Record a new code version if the deployed branch moved since the last
    recorded deploy.  Returns the new version event as a dict, or None.
    """
    from . import state
    from .backup import _mirror_to_grace
    from .config import ZenodoConfig
    from .versioning import cremona_letter_code

    cfg = config or ZenodoConfig()
    current = state.latest_versions(db)
    if current is None:
        raise RuntimeError(
            "version history is empty; run db.zenodo_setup() first")
    commit = deployed_commit(repo, branch)
    last = state.latest_code_deploy(db)
    if last is not None and last["git_hash"] == commit:
        return None
    major = major_at_commit(commit, current["major"])
    editor = cfg.editor or "deploy-watcher"
    if major > current["major"]:
        event = {"kind": "major", "major": major, "seq": 0, "git_hash": commit}
        if not dry_run:
            state.insert_major(db, major, git_hash=commit, editor=editor)
            _mirror_to_grace(cfg, "major", major, major, git_hash=commit,
                             editor=editor)
            _mirror_to_grace(cfg, "code", major, 0, git_hash=commit,
                             editor=editor, comment="code counter reset")
        print("Recorded major version bump to %s.0.a (commit %s)%s"
              % (major, commit[:12], " [dry run]" if dry_run else ""))
    else:
        seq = current["code_seq"] + 1 if major == current["major"] else 0
        event = {"kind": "code", "major": major, "seq": seq, "git_hash": commit}
        if not dry_run:
            state.insert_code(db, major, seq, commit, editor=editor)
            _mirror_to_grace(cfg, "code", major, seq, git_hash=commit,
                             editor=editor)
        print("Recorded frontend release %s.*.%s (commit %s)%s"
              % (major, cremona_letter_code(seq), commit[:12],
                 " [dry run]" if dry_run else ""))
    return event


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="report without writing to the database")
    parser.add_argument("--branch", default=BRANCH)
    args = parser.parse_args()
    from lmfdb import db
    check_deploy(db, dry_run=args.dry_run, branch=args.branch)


if __name__ == "__main__":
    main()
