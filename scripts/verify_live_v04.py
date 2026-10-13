"""Rebuild the v0.4 reserve-refund proof from StudioNet source and receipts."""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionHashVariant

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = json.loads((ROOT / "deployments" / "studionet_v0.4.json").read_text(encoding="utf-8"))
JOURNAL = ROOT / ".local" / "reserve-demo-v0.4.json"
OUTPUT = ROOT / "public" / "verification.json"
PROJECT = "MB-RESERVE-001"
AMOUNT = 2 * 10**15


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def main():
    records = json.loads(JOURNAL.read_text(encoding="utf-8"))["transactions"]
    expected_methods = ["create_project", "recover_expired", "withdraw", "reconcile_withdrawal", "release_reserve", "withdraw", "reconcile_withdrawal"]
    require([item["method"] for item in records] == expected_methods, "Reserve demo transaction sequence incomplete")
    account = Account.create()
    client = create_client(chain=studionet, account=account)
    address = DEPLOYMENT["address"]
    source = (ROOT / "contracts" / "milestone_bond_v0_4.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    local_hash = hashlib.sha256(source.encode()).hexdigest()
    require(local_hash == DEPLOYMENT["source_sha256"], "Local release source hash changed")
    encoded = client.provider.make_request(method="gen_getContractCode", params=[address]).get("result")
    require(isinstance(encoded, str), "Deployed source unavailable")
    require(base64.b64decode(encoded, validate=True).decode("utf-8").replace("\r\n", "\n") == source, "Deployed source differs")

    def read(method, args):
        return client.read_contract(address=address, function_name=method, args=args, account=account, transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)

    config = read("get_config", [])
    require(config.get("version") == "milestonebond.v0.4" and config.get("reserve_policy") == DEPLOYMENT["deployed_config"]["reserve_policy"], "Reserve policy mismatch")
    project = read("get_project", [PROJECT])
    sponsor = project["sponsor"]
    state = read("get_accounting", [sponsor])
    credit = read("get_project_accounting", [PROJECT, sponsor])
    require(project["status"] == "REFUNDED" and project["reserve_initial"] == str(AMOUNT) and project["reserve_remaining"] == "0" and project["reserve_consumed"] == "0" and project["reserve_released"] is True and project["claims_outstanding"] == "0", "Project reserve state mismatch")
    require(credit["claimable"] == "0" and state["deposited"] == str(2 * AMOUNT) and state["locked"] == "0" and state["credited"] == "0" and state["pending_out"] == "0" and state["reserve_locked"] == "0" and state["reserve_consumed"] == "0" and state["withdrawn"] == str(2 * AMOUNT) and state["contract_balance"] == "0", "Final balance invariant mismatch")

    transactions = []
    for item in records:
        tx = client.get_transaction(transaction_hash=item["hash"])
        require(tx.get("status_name") == "FINALIZED" and tx_execution_succeeded(tx), f"{item['method']} did not execute successfully")
        require(str(tx.get("to_address", "")).lower() == address.lower(), "Wrong contract target")
        entry = {"method": item["method"], "hash": item["hash"], "url": f"https://explorer-studio.genlayer.com/transactions/{item['hash']}",
                 "status": "FINALIZED", "execution_success": True}
        if item["method"] == "withdraw":
            children = tx.get("triggered_transactions") or []
            require(len(children) == 1 and children[0] == item.get("child_hash"), "Linked child mismatch")
            child = client.get_transaction(transaction_hash=children[0])
            require(child.get("status_name") == "FINALIZED" and child.get("value_credited") is True, "Child was not credited")
            require(str(child.get("triggered_by", "")).lower() == item["hash"].lower() and str(child.get("from_address", "")).lower() == address.lower() and str(child.get("to_address", "")).lower() == sponsor.lower() and int(child.get("value", 0)) == AMOUNT, "Wrong child transfer")
            entry["child"] = {"hash": children[0], "url": f"https://explorer-studio.genlayer.com/transactions/{children[0]}",
                              "value_atto": str(AMOUNT), "value_credited": True}
        transactions.append(entry)
    require(sum(item["method"] == "withdraw" for item in transactions) == 2, "Expected two separate sponsor withdrawals")

    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "network": "StudioNet", "chain_id": 61999,
              "scope": "Simulated-GEN reserve funding, escrow refund, one-time reserve release and two reconciled native payouts; not a live uncredited-child test or production insurance",
              "repository": "https://github.com/Demigodd00/milestonebond", "app_url": "https://demigodd00.github.io/milestonebond/",
              "contract": address, "contract_url": f"https://explorer-studio.genlayer.com/contracts/{address}",
              "deployment_hash": DEPLOYMENT["transaction_hash"], "source_sha256": local_hash, "source_verified": True,
              "config": config, "project_id": PROJECT, "project": project, "project_accounting": credit,
              "accounting": state, "transactions": transactions,
              "limitations": ["No external value_credited=false child was induced on StudioNet", "Reserve covers only finite losses up to its funded amount", "Sponsor reserve refund withdrawal has no additional insurance layer"]}
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"verified_v04={address} source_sha256={local_hash} transactions={len(transactions)}", flush=True)


if __name__ == "__main__":
    main()
