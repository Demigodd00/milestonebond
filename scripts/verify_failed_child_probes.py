"""Read-only verification of two isolated StudioNet internal-message probes."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionHashVariant

ROOT = Path(__file__).resolve().parents[1]


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)


def main() -> None:
    account = Account.create()
    client = create_client(chain=studionet, account=account)
    for version, source_name, record_name in (
        ("v1", "transfer_failure_probe.py", "failed_child_probe.json"),
        ("v2", "transfer_failure_probe_v2.py", "failed_child_probe_v2.json"),
    ):
        record = json.loads((ROOT / "deployments" / record_name).read_text(encoding="utf-8"))
        address = record["contract"]
        expected = (ROOT / "contracts" / source_name).read_text(encoding="utf-8").replace("\r\n", "\n")
        encoded = client.provider.make_request(method="gen_getContractCode", params=[address]).get("result")
        require(isinstance(encoded, str), f"{version}: no onchain source")
        deployed = base64.b64decode(encoded, validate=True).decode("utf-8").replace("\r\n", "\n")
        require(deployed == expected, f"{version}: source mismatch")
        require(hashlib.sha256(expected.encode()).hexdigest() == record["source_sha256"], f"{version}: source hash mismatch")
        deployment = client.get_transaction(transaction_hash=record["deployment_hash"])
        parent = client.get_transaction(transaction_hash=record["parent_hash"])
        child = client.get_transaction(transaction_hash=record["child_hash"])
        require(all(tx.get("status_name") == "FINALIZED" for tx in (deployment, parent, child)), f"{version}: not finalized")
        require(tx_execution_succeeded(deployment) and tx_execution_succeeded(parent) and not tx_execution_succeeded(child), f"{version}: wrong execution outcomes")
        require(parent.get("triggered_transactions") == [record["child_hash"]], f"{version}: wrong parent messages")
        require(str(child.get("triggered_by", "")).lower() == record["parent_hash"].lower(), f"{version}: wrong child linkage")
        require(str(child.get("from_address", "")).lower() == address.lower() and str(child.get("to_address", "")).lower() == address.lower(), f"{version}: wrong child parties")
        require(int(child.get("value", 0)) == int(record["amount_atto"]), f"{version}: wrong amount")
        require(child.get("value_credited") is True and record["child_value_credited"] is True, f"{version}: value not credited")
        state = client.read_contract(address=address, function_name="state", args=[], account=account, transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)
        require(str(state["attempted"]) == record["amount_atto"] and str(state["balance"]) == record["balance_after"] == record["amount_atto"], f"{version}: wrong balance")
        print(f"{version}: verified finalized execution failure, value_credited=true, and preserved balance")


if __name__ == "__main__":
    main()
