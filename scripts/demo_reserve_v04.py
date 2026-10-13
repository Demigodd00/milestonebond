"""Test-only StudioNet v0.4 reserve lifecycle with ignored local signers.

Run `fund`, wait for the acceptance deadline, then run `settle`. Every
submitted hash is journaled before polling so reruns never submit twice.
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
ADDRESS = json.loads((ROOT / "deployments" / "studionet_v0.4.json").read_text(encoding="utf-8"))["address"]
KEYS = ROOT / ".local" / "demo-accounts.json"
JOURNAL = ROOT / ".local" / "reserve-demo-v0.4.json"
PROJECT = "MB-RESERVE-001"
FIRST_REQUEST = "d" * 64
SECOND_REQUEST = "e" * 64
AMOUNT = 2 * 10**15


def accounts():
    keys = json.loads(KEYS.read_text(encoding="utf-8"))
    return {role: Account.from_key(key) for role, key in keys.items()}


def client(role="sponsor"):
    return create_client(chain=studionet, account=accounts()[role])


def journal():
    return json.loads(JOURNAL.read_text(encoding="utf-8")) if JOURNAL.exists() else {"project": PROJECT, "transactions": []}


def save(record):
    JOURNAL.parent.mkdir(exist_ok=True)
    JOURNAL.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def read(method, args):
    c = client()
    return c.read_contract(address=ADDRESS, function_name=method, args=args, account=accounts()["sponsor"], transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)


def write(method, args, value=0):
    record = journal()
    request = args[1] if method == "withdraw" else args[0] if method == "reconcile_withdrawal" else None
    if any(item["method"] == method and item.get("request") == request for item in record["transactions"]):
        raise RuntimeError(f"{method} already journaled; inspect its hash before retrying")
    c = client()
    tx = str(c.write_contract(address=ADDRESS, function_name=method, args=args, value=value))
    item = {"method": method, "request": request,
            "hash": tx, "submitted_at": datetime.now(timezone.utc).isoformat()}
    record["transactions"].append(item)
    save(record)
    print(f"{method} submitted={tx}", flush=True)
    receipt = c.wait_for_transaction_receipt(transaction_hash=tx, status=TransactionStatus.FINALIZED, interval=3000, retries=120, full_transaction=True)
    item["finalized"] = receipt.get("status_name") == "FINALIZED"
    item["execution_success"] = tx_execution_succeeded(receipt)
    save(record)
    if not item["finalized"] or not item["execution_success"]:
        raise RuntimeError(f"{method} finalized without success: {tx}")
    return tx


def child(parent):
    c = client()
    receipt = c.get_transaction(transaction_hash=parent)
    children = receipt.get("triggered_transactions") or []
    if len(children) != 1:
        raise RuntimeError("Expected exactly one linked native child")
    linked = c.wait_for_transaction_receipt(transaction_hash=children[0], status=TransactionStatus.FINALIZED, interval=3000, retries=120, full_transaction=True)
    if linked.get("status_name") != "FINALIZED" or linked.get("value_credited") is not True:
        raise RuntimeError("Native child did not finalize with value_credited=true")
    record = journal()
    item = next(x for x in record["transactions"] if x["hash"] == parent)
    item["child_hash"] = children[0]
    item["child_value_credited"] = True
    save(record)
    print(f"linked_child={children[0]}", flush=True)


def fund():
    from demo_operator import terms

    author = accounts()["author"].address
    frozen = terms(author)
    frozen["id"] = PROJECT
    frozen["title"] = "Reserve-backed project expiration fixture"
    frozen["accept_by"] = int(datetime.now(timezone.utc).timestamp()) + 650
    write("create_project", [json.dumps(frozen)], 2 * AMOUNT)
    project = read("get_project", [PROJECT])
    accounting = read("get_accounting", [author])
    if project["reserve_initial"] != str(AMOUNT) or accounting["locked"] != str(AMOUNT) or accounting["reserve_locked"] != str(AMOUNT):
        raise RuntimeError("Live reserve and escrow accounting mismatch")
    print(f"funded_project={PROJECT} accept_by={project['accept_by']} reserve={project['reserve_initial']}", flush=True)


def settle():
    project = read("get_project", [PROJECT])
    if int(datetime.now(timezone.utc).timestamp()) < project["accept_by"]:
        raise RuntimeError(f"Acceptance deadline not reached: {project['accept_by']}")
    sponsor = accounts()["sponsor"].address
    write("recover_expired", [PROJECT])
    if read("get_project", [PROJECT])["status"] != "REFUNDED":
        raise RuntimeError("Expected refunded project")
    if read("get_project_accounting", [PROJECT, sponsor])["claimable"] != str(AMOUNT):
        raise RuntimeError("Sponsor escrow refund credit missing")
    first = write("withdraw", [PROJECT, FIRST_REQUEST])
    child(first)
    write("reconcile_withdrawal", [first])
    if read("get_project", [PROJECT])["claims_outstanding"] != "0":
        raise RuntimeError("Escrow refund claim not cleared")
    write("release_reserve", [PROJECT])
    if read("get_project_accounting", [PROJECT, sponsor])["claimable"] != str(AMOUNT):
        raise RuntimeError("Unused reserve not returned as sponsor credit")
    second = write("withdraw", [PROJECT, SECOND_REQUEST])
    child(second)
    write("reconcile_withdrawal", [second])
    state = read("get_accounting", [sponsor])
    if state["locked"] != "0" or state["credited"] != "0" or state["pending_out"] != "0" or state["reserve_locked"] != "0" or state["withdrawn"] != str(2 * AMOUNT):
        raise RuntimeError("Final accounting mismatch")
    print(json.dumps({"project": PROJECT, "accounting": state}, indent=2), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("fund", "settle", "status"):
        raise SystemExit("Usage: demo_reserve_v04.py fund|settle|status")
    {"fund": fund, "settle": settle, "status": lambda: print(json.dumps({"project": read("get_project", [PROJECT]), "accounting": read("get_accounting", [accounts()["sponsor"].address])}, indent=2))}[sys.argv[1]]()
