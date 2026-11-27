"""
Reading a "Move data to production" request (the issue form in
``.github/ISSUE_TEMPLATE/data-to-prod.yml``) from GitHub, for
``LMFDBDatabase.update_prod_from_issue``.

Issues are public, so this uses the GitHub REST API without a token.
"""

import re

ISSUE_REPO = "LMFDB/lmfdb"

# The labels of the form's fields, which head the sections of the issue body
TABLES = "Tables"
DESCRIPTION = "Description of the change"
BUMP = "Version update"
PER_TABLE = "Per-table details (optional)"

NO_RESPONSE = "_No response_"
TABLE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
PER_TABLE_LINE = re.compile(
    r"^[-*\s]*`?([a-z][a-z0-9_]*)`?\s*:\s*(major|minor)\b[\s,;:.\-]*(.*)$",
    re.IGNORECASE)


def fetch_issue(number, repo=ISSUE_REPO):
    """The issue's JSON from the GitHub REST API."""
    import requests
    resp = requests.get("https://api.github.com/repos/%s/issues/%s"
                        % (repo, int(number)),
                        headers={"Accept": "application/vnd.github+json"},
                        timeout=30)
    resp.raise_for_status()
    return resp.json()


def form_sections(body):
    """``{label: text}`` for the ``### label`` sections of an issue form body."""
    parts = re.split(r"^### (.+?)\s*$", (body or "").replace("\r\n", "\n"),
                     flags=re.M)
    sections = {}
    for label, text in zip(parts[1::2], parts[2::2]):
        text = text.strip()
        sections[label] = "" if text == NO_RESPONSE else text
    return sections


def change_request(issue):
    """
    The push requested by an issue (the JSON from ``fetch_issue``), as a dict
    with keys ``tables`` (list), ``description`` and ``bump`` (each a string,
    or a dict by table when the per-table details differ), ``url``,
    ``title``, ``author`` and ``updated``.  Raises ValueError if the issue
    was not made with the form, is closed, or cannot be read unambiguously.
    """
    url = issue.get("html_url")
    if "pull_request" in issue:
        raise ValueError("%s is a pull request, not a data request" % url)
    if issue.get("state") != "open":
        raise ValueError("%s is closed; reopen it, or call update_prod "
                         "directly" % url)
    sections = form_sections(issue.get("body"))
    missing = [label for label in (TABLES, DESCRIPTION, BUMP)
               if not sections.get(label)]
    if missing:
        raise ValueError("%s has no %s section: was it made with the 'Move "
                         "data to production' form?" % (url, ", ".join(missing)))

    tables = [t.strip("`") for t in re.split(r"[\s,]+", sections[TABLES])
              if t.strip("`-*")]
    bad = [t for t in tables if not TABLE_NAME.match(t)]
    if bad or not tables:
        raise ValueError("%s: cannot read table names %s" % (url, bad))

    description = sections[DESCRIPTION]
    bump = sections[BUMP].strip().lower()
    per_bump, per_description = {}, {}
    for line in sections.get(PER_TABLE, "").splitlines():
        if not line.strip():
            continue
        m = PER_TABLE_LINE.match(line.strip())
        if m is None or m.group(1) not in tables:
            raise ValueError("%s: cannot read the per-table line %r; it "
                             "should be `table: major/minor, description` for "
                             "one of the tables listed" % (url, line))
        per_bump[m.group(1)] = m.group(2).lower()
        if m.group(3).strip():
            per_description[m.group(1)] = m.group(3).strip()

    if bump.startswith("different"):
        unset = [t for t in tables if t not in per_bump]
        if unset:
            raise ValueError("%s: no version update given for %s"
                             % (url, ", ".join(unset)))
    elif bump not in ("major", "minor"):
        raise ValueError("%s: unknown version update %r" % (url, bump))
    if per_bump or bump.startswith("different"):
        bump = {t: per_bump.get(t, bump) for t in tables}
    if per_description:
        description = {t: per_description.get(t, description) for t in tables}
    return {
        "tables": tables,
        "description": description,
        "bump": bump,
        "url": url,
        "title": issue.get("title"),
        "author": (issue.get("user") or {}).get("login"),
        "updated": issue.get("updated_at"),
    }


def summary(request):
    """A human-readable account of a change request, for confirmation."""
    lines = ["%s" % request["url"],
             "  %s (by %s, last updated %s)"
             % (request["title"], request["author"], request["updated"])]
    for t in request["tables"]:
        bump, description = request["bump"], request["description"]
        if isinstance(bump, dict):
            bump = bump[t]
        if isinstance(description, dict):
            description = description[t]
        lines.append("  %-30s %s: %s" % (t, bump, description))
    return "\n".join(lines)
