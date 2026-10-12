"""Test-only StudioNet operator for the public two-stage fixture.

Generated account keys stay in ignored .local/demo-accounts.json. Never use
these accounts on another network or with real-value assets.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionHashVariant, TransactionStatus

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".local" / "demo-accounts.json"
JOURNAL = ROOT / ".local" / "demo-state.json"
ADDRESS = json.loads((ROOT / "deployments" / "studionet.json").read_text(encoding="utf-8"))["address"]
PROJECT = "MB-LIVE-001"


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def accounts():
    if not PRIVATE.exists():
        keys = {role: Account.create().key.hex() for role in ("sponsor", "author")}
        save(PRIVATE, keys)
    keys = json.loads(PRIVATE.read_text(encoding="utf-8"))
    return {role: Account.from_key(key) for role, key in keys.items()}


def client(role: str):
    return create_client(chain=studionet, account=accounts()[role])


def read():
    c = client("sponsor")
    return c.read_contract(address=ADDRESS, function_name="get_project", args=[PROJECT], account=accounts()["sponsor"], transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)


def write(role: str, method: str, args: list, value: int = 0):
    c = client(role)
    tx = c.write_contract(address=ADDRESS, function_name=method, args=args, value=value)
    state = json.loads(JOURNAL.read_text(encoding="utf-8")) if JOURNAL.exists() else {"project": PROJECT, "transactions": []}
    state["transactions"].append({"role": role, "method": method, "hash": str(tx), "args": args, "at": datetime.now(timezone.utc).isoformat()})
    save(JOURNAL, state)
    print(f"submitted={tx} method={method}", flush=True)
    receipt = c.wait_for_transaction_receipt(transaction_hash=tx, status=TransactionStatus.FINALIZED, interval=3000, retries=120, full_transaction=True)
    outcome = {"status": receipt.get("status_name") or receipt.get("statusName"), "execution_success": tx_execution_succeeded(receipt)}
    state["transactions"][-1]["outcome"] = outcome
    save(JOURNAL, state)
    print(json.dumps(outcome), flush=True)
    if not outcome["execution_success"]:
        print(json.dumps(receipt, default=str)[:6000], flush=True)
        raise SystemExit("Transaction did not execute successfully")
    return tx


def terms(author: str):
    now = int(datetime.now(timezone.utc).timestamp())
    return {"id": PROJECT, "title": "Two-stage public order API fixture", "repo": "Demigodd00/milestonebond", "issue_number": 1,
            "issue_sha256": "623020dff6c8e6969e81f5683fdea938d29cc810726b31afd92f756f97d39bb9",
            "base_sha": "94d80d7b2eab03baff1c65b55216aa31eb98f652", "author": author,
            "workflow_path": ".github/workflows/demo-ci.yml", "workflow_sha256": "4547736e52e9f094a9308f6dca3e1be8a45f551d3ba72a4c62ac04e6c69febe1",
            "workflow_bytes": 414, "workflow_id": 381723182, "required_job": "acceptance", "accept_by": now + 3600,
            "milestones": [
                {"title": "Idempotent order creation", "criteria": ["Repeated calls with the same nonempty key return the same order record, not a newly numbered order."], "allowed_paths": ["examples/order_service.py"], "due_at": now + 86400, "amount": 10**15},
                {"title": "Reject empty keys", "criteria": ["An empty key raises ValueError while repeated nonempty keys still return their original order record."], "allowed_paths": ["examples/order_service.py"], "due_at": now + 2*86400, "amount": 10**15},
            ]}


def main():
    command, *args = sys.argv[1:]
    identities = accounts()
    if command == "accounts":
        print(json.dumps({role: account.address for role, account in identities.items()}, indent=2))
    elif command == "fund":
        role = args[0]
        if role != "sponsor":
            raise SystemExit("Only the sponsor needs simulated funding")
        result = client(role).provider.make_request(method="sim_fundAccount", params=[identities[role].address, 100000000000000000])
        print(json.dumps(result, default=str))
    elif command == "create":
        write("sponsor", "create_project", [json.dumps(terms(identities["author"].address))], 2*10**15)
    elif command == "accept":
        write("author", "accept_project", [PROJECT])
    elif command == "submit":
        pr, head, run, attempt = args
        write("author", "submit_milestone", [PROJECT, int(pr), head, int(run), int(attempt)])
    elif command == "review":
        write("sponsor", "review_milestone", [PROJECT, read()["milestones"][read()["current"]]["revision"]])
    elif command == "finalize":
        write("sponsor", "finalize_milestone", [PROJECT])
    elif command == "state":
        print(json.dumps(read(), indent=2, default=str))
    else:
        raise SystemExit("Usage: demo_operator.py accounts|fund|create|accept|submit PR HEAD RUN ATTEMPT|review|finalize|state")


if __name__ == "__main__":
    main()
