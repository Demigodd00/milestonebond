"""Read-only preflight for the public GitHub commitments used by v0.5 demo."""
from __future__ import annotations

import hashlib
import json
import urllib.request

from demo_operator import terms


def get(url: str, *, raw: bool = False):
    request = urllib.request.Request(url, headers={"User-Agent": "MilestoneBond-preflight",
                                                   "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=25) as response:
        data = response.read()
    return data.decode("utf-8") if raw else json.loads(data)


def main():
    fixture = terms("0x0000000000000000000000000000000000000001")
    repo = fixture["repo"]
    repository = get(f"https://api.github.com/repos/{repo}")
    user = get(f"https://api.github.com/users/{fixture['author_github_login']}")
    issue = get(f"https://api.github.com/repos/{repo}/issues/{fixture['issue_number']}")
    base = get(f"https://api.github.com/repos/{repo}/git/commits/{fixture['base_sha']}")
    workflow = get(f"https://raw.githubusercontent.com/{repo}/{fixture['base_sha']}/{fixture['workflow_path']}", raw=True)
    checks = {
        "public_canonical_repository": repository.get("private") is False and repository.get("full_name", "").lower() == repo.lower(),
        "author_github_id": user.get("id") == fixture["author_github_id"],
        "issue_body_hash": hashlib.sha256(issue.get("body", "").encode()).hexdigest() == fixture["issue_sha256"],
        "base_commit": base.get("sha") == fixture["base_sha"],
        "workflow_hash_and_bytes": hashlib.sha256(workflow.encode()).hexdigest() == fixture["workflow_sha256"]
            and len(workflow.encode()) == fixture["workflow_bytes"],
    }
    print(json.dumps(checks, indent=2), flush=True)
    if not all(checks.values()):
        raise RuntimeError("Live GitHub fixture differs from frozen source commitments")


if __name__ == "__main__":
    main()
