"""Test-only StudioNet experiment: an IC child rejects simulated GEN.

This is deliberately *not* the external EOA transfer used by MilestoneBond.
It measures the protocol's internal-message failure semantics only.
"""
from __future__ import annotations

import hashlib
import base64
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionHashVariant, TransactionStatus

ROOT = Path(__file__).resolve().parents[1]
KEYS = ROOT / ".local" / "demo-accounts.json"
AMOUNT = 10**15


def require(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError(why)


def main() -> None:
    require(len(sys.argv) == 3 and sys.argv[2] in ("v1", "v2"),
            "Usage: probe_failed_child.py <deployment-hash> <v1|v2>")
    version = sys.argv[2]
    source_path = ROOT / "contracts" / ("transfer_failure_probe.py" if version == "v1" else "transfer_failure_probe_v2.py")
    output_path = ROOT / "deployments" / ("failed_child_probe.json" if version == "v1" else "failed_child_probe_v2.json")
    require(not output_path.exists(), "Existing probe record: refusing a second run")
    require(sys.argv[1].startswith("0x") and len(sys.argv[1]) == 66,
            "Pass an existing finalized probe deployment hash; do not deploy twice")
    key = json.loads(KEYS.read_text(encoding="utf-8"))["sponsor"]
    account = Account.from_key(key)
    client = create_client(chain=studionet, account=account)
    source = source_path.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(source.replace("\r\n", "\n").encode()).hexdigest()

    deploy_hash = sys.argv[1]
    print(f"probe_deployment={deploy_hash}", flush=True)
    deploy = client.wait_for_transaction_receipt(transaction_hash=deploy_hash, status=TransactionStatus.FINALIZED, interval=3000, retries=120, full_transaction=True)
    require(deploy.get("status_name") == "FINALIZED" and tx_execution_succeeded(deploy), "Probe deployment failed")
    address = (deploy.get("tx_data_decoded") or {}).get("contract_address") or (deploy.get("data") or {}).get("contract_address")
    require(isinstance(address, str) and len(address) == 42, "Probe address unavailable")
    encoded = client.provider.make_request(method="gen_getContractCode", params=[address]).get("result")
    require(isinstance(encoded, str), "Probe onchain source unavailable")
    deployed = base64.b64decode(encoded, validate=True).decode("utf-8")
    require(hashlib.sha256(deployed.replace("\r\n", "\n").encode()).hexdigest() == source_hash,
            "Probe onchain source differs from local source")
    print(f"probe_address={address}", flush=True)
    before = client.read_contract(address=address, function_name="state", args=[], transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)

    parent_hash = str(client.write_contract(address=address, function_name="trigger", args=[], value=AMOUNT))
    print(f"probe_parent={parent_hash}", flush=True)
    parent = client.wait_for_transaction_receipt(transaction_hash=parent_hash, status=TransactionStatus.FINALIZED, interval=3000, retries=120, full_transaction=True)
    require(parent.get("status_name") == "FINALIZED" and tx_execution_succeeded(parent), "Probe parent failed")
    children = parent.get("triggered_transactions") or []
    require(len(children) == 1, "Probe did not emit exactly one child")
    child_hash = children[0]
    print(f"probe_child={child_hash}", flush=True)

    child = None
    for _ in range(60):
        child = client.get_transaction(transaction_hash=child_hash)
        if child.get("status_name") == "FINALIZED":
            break
        time.sleep(3)
    require(child is not None and child.get("status_name") == "FINALIZED", "Probe child did not finalize")
    require(str(child.get("triggered_by", "")).lower() == parent_hash.lower(), "Wrong child parent")
    require(str(child.get("from_address", "")).lower() == address.lower() and str(child.get("to_address", "")).lower() == address.lower(), "Wrong child parties")
    require(int(child.get("value", 0)) == AMOUNT, "Wrong child value")
    after = client.read_contract(address=address, function_name="state", args=[], transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)
    require(not tx_execution_succeeded(child), "Receiver unexpectedly accepted child")
    require(str(after["attempted"]) == str(AMOUNT), "Probe state missing attempt")
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "network": "StudioNet",
        "scope": "Isolated internal IC-to-IC failed-message probe; not MilestoneBond external EOA withdrawal evidence",
        "amount_atto": str(AMOUNT),
        "source_sha256": source_hash,
        "source_verified": True,
        "contract": address,
        "deployment_hash": deploy_hash,
        "parent_hash": parent_hash,
        "parent_execution_success": True,
        "child_hash": child_hash,
        "child_execution_success": False,
        "child_value_credited": child.get("value_credited"),
        "child_linkage_verified": True,
        "balance_before": str(before["balance"]),
        "balance_after": str(after["balance"]),
    }
    output_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    main()
