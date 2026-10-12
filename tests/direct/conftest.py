import hashlib
import json
import re
import sys
from datetime import datetime, timezone

import pytest

NOW = 2_000_000_000
REPO = "fixture/milestones"
BASE, HEAD1, HEAD2, BAD = "a" * 40, "b" * 40, "c" * 40, "d" * 40
ISSUE = "Build an idempotent order API in two independently reviewed stages."
WORKFLOW = "name: MilestoneBond\non: push\njobs:\n  acceptance:\n    runs-on: ubuntu-latest\n"
BEFORE = "def create_order(key):\n    return new_order(key)\n"
AFTER1 = "def create_order(key):\n    if key in orders: return orders[key]\n    return new_order(key)\n"
AFTER2 = "def create_order(key):\n    if key in orders: return orders[key]\n    if not key: raise ValueError('key required')\n    return new_order(key)\n"
ID = "MB-ORDER-001"


def iso(n):
    return datetime.fromtimestamp(n, tz=timezone.utc).isoformat()


def addr(account):
    return "0x" + account.hex()


@pytest.fixture(autouse=True)
def clock(direct_vm):
    original = direct_vm.warp

    def warp(value):
        original(value)
        for module in tuple(sys.modules.values()):
            raw = getattr(getattr(module, "gl", None), "message_raw", None)
            if isinstance(raw, dict) and "datetime" in raw:
                raw["datetime"] = value

    direct_vm.warp = warp
    warp(iso(NOW))


def mock(vm, *, base=BASE, head=HEAD1, run_id=101, pr=11, status="SUPPORTED", issue=ISSUE, workflow=WORKFLOW, after=AFTER1, run_started=NOW, overrides=None, quote_override=None):
    overrides = overrides or {}
    vm.clear_mocks()
    records = {
        "": {"id": 77, "private": False, "full_name": REPO},
        "/issues/7": {"number": 7, "body": issue},
        "/git/commits/" + BASE: {"sha": BASE},
        "/commits/" + head + "?per_page=100": {"sha": head, "parents": [{"sha": base}], "files": [{"filename": "src/orders.py", "status": "modified"}]},
        "/pulls/" + str(pr): {"number": pr, "head": {"sha": head, "repo": {"id": 77}}, "base": {"repo": {"id": 77}}},
        f"/actions/runs/{run_id}/attempts/1": {"id": run_id, "run_attempt": 1, "head_sha": head, "head_repository": {"id": 77}, "repository": {"id": 77}, "workflow_id": 55, "path": ".github/workflows/ci.yml@main", "event": "push", "status": "completed", "conclusion": "success", "run_started_at": iso(run_started)},
        f"/actions/runs/{run_id}/attempts/1/jobs?per_page=100": {"total_count": 1, "jobs": [{"id": 1000 + run_id, "run_id": run_id, "head_sha": head, "name": "acceptance", "status": "completed", "conclusion": "success", "steps": [{"number": 1, "name": "tests", "status": "completed", "conclusion": "success"}]}]},
    }
    for suffix, patch in overrides.items():
        records[suffix].update(patch)
    for suffix, value in records.items():
        vm.mock_web("^" + re.escape("https://api.github.com/repos/" + REPO + suffix) + "$", {"status": 200, "body": json.dumps(value)})
    for commit, source in [(BASE, BEFORE), (HEAD1, AFTER1), (HEAD2, AFTER2), (BAD, after)]:
        if commit == head:
            source = after
        vm.mock_web("^" + re.escape(f"https://raw.githubusercontent.com/{REPO}/{commit}/.github/workflows/ci.yml") + "$", {"status": 200, "body": workflow})
        vm.mock_web("^" + re.escape(f"https://raw.githubusercontent.com/{REPO}/{commit}/src/orders.py") + "$", {"status": 200, "body": source})
    quote = quote_override if quote_override is not None else ("if key in orders: return orders[key]" if head == HEAD1 else "if not key: raise ValueError('key required')")
    vm.mock_llm("MILESTONEBOND_REVIEW_V1", json.dumps({"scope_ok": True, "checks": [{"id": "C1", "status": status, "quote": quote if status == "SUPPORTED" else "", "reason": "The complete source supports this criterion."}]}))


def terms(author):
    return {"id": ID, "title": "Safer order API", "repo": REPO, "issue_number": 7,
            "issue_sha256": hashlib.sha256(ISSUE.encode()).hexdigest(), "base_sha": BASE, "author": addr(author),
            "workflow_path": ".github/workflows/ci.yml", "workflow_sha256": hashlib.sha256(WORKFLOW.encode()).hexdigest(),
            "workflow_bytes": len(WORKFLOW.encode()), "workflow_id": 55, "required_job": "acceptance", "accept_by": NOW + 1200,
            "milestones": [
                {"title": "Idempotency", "criteria": ["Repeated keys return the original order."], "allowed_paths": ["src/orders.py"], "due_at": NOW + 3600, "amount": 10**16},
                {"title": "Input validation", "criteria": ["Empty keys raise an error."], "allowed_paths": ["src/orders.py"], "due_at": NOW + 7200, "amount": 2 * 10**16},
            ]}


@pytest.fixture
def scenario(direct_vm, direct_deploy, direct_alice, direct_bob):
    mock(direct_vm)
    contract = direct_deploy("contracts/milestone_bond.py")
    direct_vm.sender = direct_alice
    direct_vm.deal(direct_alice, 10**18)
    direct_vm.value = 3 * 10**16
    contract.create_project(json.dumps(terms(direct_bob)))
    direct_vm.value = 0
    return contract, direct_alice, direct_bob
