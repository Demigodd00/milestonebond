"""Deploy and verify MilestoneBond on gasless StudioNet with a disposable signer.

No admin key is needed; the deployment signer is not saved. This script never
claims production funding or browser-wallet verification.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionHashVariant, TransactionStatus

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "contracts" / "milestone_bond.py"
JOURNAL = ROOT / "deployments" / "pending.json"
RECORD = ROOT / "deployments" / "studionet.json"
PUBLIC = ROOT / "public" / "deployment.json"


def hash_source(source: str) -> str:
    return hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def main() -> None:
    if RECORD.exists():
        raise SystemExit("Deployment record exists; refusing a duplicate deployment")
    if JOURNAL.exists():
        raise SystemExit("A deployment hash is already journaled; inspect it before retrying")
    account = Account.create()
    source = SOURCE.read_text(encoding="utf-8")
    client = create_client(chain=studionet, account=account)
    print(f"network=studionet signer={account.address} source_sha256={hash_source(source)}", flush=True)
    tx = client.deploy_contract(code=source, account=account, args=[])
    JOURNAL.parent.mkdir(exist_ok=True)
    JOURNAL.write_text(json.dumps({"network": "studionet", "transaction_hash": str(tx), "source_sha256": hash_source(source)}, indent=2) + "\n", encoding="utf-8")
    print(f"transaction={tx}", flush=True)
    receipt = client.wait_for_transaction_receipt(transaction_hash=tx, status=TransactionStatus.FINALIZED, interval=3000, retries=120, full_transaction=True)
    if (receipt.get("status_name") or receipt.get("statusName")) != "FINALIZED" or not tx_execution_succeeded(receipt):
        raise RuntimeError("Deployment finalized without successful execution; inspect the journaled hash and receipt")
    address = None
    for key in ("tx_data_decoded", "data"):
        value = receipt.get(key)
        if isinstance(value, dict) and value.get("contract_address"):
            address = str(value["contract_address"])
            break
    if not address or re.fullmatch(r"0x[0-9a-fA-F]{40}", address) is None:
        raise RuntimeError("Successful receipt has no valid contract address")
    encoded = client.provider.make_request(method="gen_getContractCode", params=[address]).get("result")
    if not isinstance(encoded, str):
        raise RuntimeError("Cannot read deployed source")
    deployed = base64.b64decode(encoded, validate=True).decode("utf-8")
    if hash_source(deployed) != hash_source(source):
        raise RuntimeError("Onchain source differs from local release")
    config = client.read_contract(address=address, function_name="get_config", args=[], account=account, transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)
    if not isinstance(config, dict) or config.get("version") != "milestonebond.v0.2" or config.get("challenge_seconds") != 600 or config.get("fee_bps") != 0:
        raise RuntimeError("Onchain config differs from local release")
    record = {"contract": "MilestoneBond", "version": "milestonebond.v0.2", "network": "studionet", "chain_id": 61999,
              "address": address, "transaction_hash": str(tx), "deployer": account.address,
              "signer_mode": "disposable_deployment_only", "source_sha256": hash_source(source),
              "runner_dependency": source.splitlines()[0], "receipt_status": "FINALIZED", "execution_result": "SUCCESS",
              "verified_source_and_config": True, "deployed_config": config, "deployed_at": datetime.now(timezone.utc).isoformat()}
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    PUBLIC.write_text(json.dumps({"verified": True, "address": address, "chainId": 61999, "sourceSha256": record["source_sha256"],
                                  "version": record["version"], "network": "studionet"}, indent=2) + "\n", encoding="utf-8")
    JOURNAL.unlink()
    print(f"verified_contract={address}", flush=True)


if __name__ == "__main__":
    main()
