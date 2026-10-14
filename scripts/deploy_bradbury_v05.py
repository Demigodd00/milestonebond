"""Submit once, then independently verify a finalized MilestoneBond v0.5 release.

Usage: python scripts/deploy_bradbury_v05.py submit|verify
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.abi import calldata
from genlayer_py.abi.transactions import serialize
from genlayer_py.chains import testnet_bradbury
from genlayer_py.contracts.actions import _encode_add_transaction_data, _prepare_transaction
from genlayer_py.contracts.utils import make_calldata_object
from web3.constants import ADDRESS_ZERO
from bradbury_read import read_final

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "contracts" / "milestone_bond_v0_5_packed.py"
JOURNAL = ROOT / ".local" / "bradbury_v0.5.pending.json"
RECORD = ROOT / "deployments" / "bradbury_v0.5.json"


def account():
    key = json.loads((ROOT / ".local" / "demo-accounts.json").read_text(encoding="utf-8"))["sponsor"]
    signer = Account.from_key(key)
    if signer.address.lower() != "0x0bcbcde568096ea2c93e71d5f33acd45be00590e":
        raise RuntimeError("Unexpected funded signer")
    return signer


def source_hash(source: str) -> str:
    return hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def estimate() -> None:
    signer = account()
    client = create_client(chain=testnet_bradbury, account=signer)
    source = SOURCE.read_text(encoding="utf-8")
    serialized = serialize([source, calldata.encode(make_calldata_object(method=None, args=[])), False])
    encoded = _encode_add_transaction_data(
        self=client, sender_account=signer, recipient=ADDRESS_ZERO,
        consensus_max_rotations=client.chain.default_consensus_max_rotations,
        data=serialized)
    prepared = _prepare_transaction(self=client, sender=signer.address,
                                    recipient=client.chain.consensus_main_contract["address"],
                                    data=encoded, value=0)
    print({"source_bytes": len(source.encode("utf-8")),
           "estimated_gas": int(prepared["gas"], 16),
           "block_gas_limit": client.w3.eth.get_block("latest")["gasLimit"],
           "calldata_bytes": len(bytes.fromhex(encoded[2:]))}, flush=True)


def submit() -> None:
    if JOURNAL.exists() or RECORD.exists():
        raise RuntimeError("MilestoneBond v0.5 already submitted or recorded; do not duplicate")
    source = SOURCE.read_text(encoding="utf-8")
    if not source.startswith('# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }'):
        raise RuntimeError("Unexpected GenVM runner dependency")
    signer = account()
    client = create_client(chain=testnet_bradbury, account=signer)
    if client.w3.eth.chain_id != 4221:
        raise RuntimeError("Wrong chain")
    if client.w3.eth.get_balance(signer.address) < 10**18:
        raise RuntimeError("Keep at least 1 GEN for demo and fees")
    txid = str(client.deploy_contract(code=source, account=signer, args=[]))
    JOURNAL.parent.mkdir(exist_ok=True)
    JOURNAL.write_text(json.dumps({"network": "bradbury", "chain_id": 4221,
                                   "transaction_id": txid, "signer": signer.address,
                                   "source_sha256": source_hash(source),
                                   "submitted_at": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n",
                       encoding="utf-8")
    print(f"milestonebond_v0.5_transaction_id={txid}", flush=True)


def verify() -> None:
    if RECORD.exists():
        raise RuntimeError("Verified deployment record already exists")
    journal = json.loads(JOURNAL.read_text(encoding="utf-8"))
    source = SOURCE.read_text(encoding="utf-8")
    if source_hash(source) != journal["source_sha256"]:
        raise RuntimeError("Local source changed after submission")
    signer = account()
    client = create_client(chain=testnet_bradbury, account=signer)
    raw = client.w3.provider.make_request("gen_getTransactionReceipt",
                                          [{"txId": journal["transaction_id"]}])
    receipt = raw.get("result") or {}
    if receipt.get("status") != 7 or receipt.get("txExecutionResult") != 1:
        print({"status": receipt.get("status"), "execution": receipt.get("txExecutionResult")}, flush=True)
        raise RuntimeError("Deployment is not finalized with successful execution")
    address = receipt.get("recipient")
    if not isinstance(address, str) or re.fullmatch(r"0x[0-9a-fA-F]{40}", address) is None:
        raise RuntimeError(f"No contract address in finalized receipt: {str(receipt)[:800]}")
    response = client.provider.make_request(method="gen_getContractCode",
                                            params=[{"address": address, "status": "finalized"}])
    encoded = response.get("result")
    if not isinstance(encoded, str):
        raise RuntimeError("Cannot read deployed contract source")
    deployed = base64.b64decode(encoded, validate=True).decode("utf-8")
    if source_hash(deployed) != journal["source_sha256"]:
        raise RuntimeError("Deployed source differs from release")
    config = read_final(client, address, signer.address, "get_config", [])
    if config.get("version") != "milestonebond.v0.5" or config.get("network_scope") != "bradbury-testnet-only":
        raise RuntimeError("Deployed policy differs from release")
    record = {"contract": "MilestoneBond", "version": "milestonebond.v0.5",
              "network": "bradbury", "chain_id": 4221, "address": address,
              "transaction_id": journal["transaction_id"], "deployer": signer.address,
              "source_sha256": journal["source_sha256"],
              "runner_dependency": source.splitlines()[0],
              "receipt_status": "FINALIZED", "execution_result": "SUCCESS",
              "verified_source_and_config": True, "deployed_config": config,
              "verified_at": datetime.now(timezone.utc).isoformat()}
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    JOURNAL.unlink()
    print(f"verified_milestonebond_v0.5={address}", flush=True)


if __name__ == "__main__":
    {"estimate": estimate, "submit": submit, "verify": verify}[sys.argv[1]]()
