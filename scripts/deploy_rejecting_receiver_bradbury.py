"""Deploy a minimal EVM receiver whose runtime always reverts on Bradbury.

The creation bytecode copies the five-byte runtime 0x60006000fd (REVERT(0,0))
from offset 12 and returns it. This is a test fixture, not a user-facing IC.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from web3 import Web3
from genlayer_py.chains import testnet_bradbury

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "contracts" / "rejecting_receiver.evm.hex"
JOURNAL = ROOT / ".local" / "rejecting_receiver_bradbury.pending.json"
RECORD = ROOT / "deployments" / "bradbury_rejecting_receiver.json"
EXPECTED_CREATION = "6005600c60003960056000f360006000fd"
EXPECTED_RUNTIME = bytes.fromhex("60006000fd")


def main() -> None:
    if RECORD.exists() or JOURNAL.exists():
        raise SystemExit("Existing receiver deployment or pending transaction; inspect it, do not repeat")
    creation_hex = SOURCE.read_text(encoding="ascii").strip()
    if creation_hex != EXPECTED_CREATION:
        raise RuntimeError("Receiver bytecode differs from reviewed fixture")
    key = json.loads((ROOT / ".local" / "demo-accounts.json").read_text(encoding="utf-8"))["sponsor"]
    signer = Account.from_key(key)
    if signer.address.lower() != "0x0bcbcde568096ea2c93e71d5f33acd45be00590e":
        raise RuntimeError("Unexpected funded test signer")
    w3 = Web3(Web3.HTTPProvider(testnet_bradbury.rpc_urls["default"]["http"][0]))
    if w3.eth.chain_id != 4221:
        raise RuntimeError("Wrong chain")
    creation = bytes.fromhex(creation_hex)
    nonce = w3.eth.get_transaction_count(signer.address)
    gas_estimate = w3.eth.estimate_gas({"from": signer.address, "data": creation})
    base_fee = w3.eth.get_block("latest")["baseFeePerGas"]
    gas_limit = (gas_estimate * 12 + 9) // 10
    maximum_fee = base_fee + w3.to_wei(2, "gwei")
    balance = w3.eth.get_balance(signer.address)
    if balance < gas_limit * maximum_fee + w3.to_wei(1, "ether"):
        raise RuntimeError("Keep at least 1 GEN untouched for the IC test")
    tx = {"from": signer.address, "nonce": nonce, "chainId": 4221,
          "data": creation, "gas": gas_limit, "maxFeePerGas": maximum_fee,
          "maxPriorityFeePerGas": w3.to_wei(2, "gwei"), "value": 0}
    signed = signer.sign_transaction(tx)
    tx_hash = w3.to_hex(signed.hash)
    JOURNAL.parent.mkdir(exist_ok=True)
    JOURNAL.write_text(json.dumps({"chain_id": 4221, "tx_hash": tx_hash,
                                   "nonce": nonce, "gas_limit": gas_limit,
                                   "creation_sha256": hashlib.sha256(creation).hexdigest()}, indent=2) + "\n",
                       encoding="utf-8")
    print(f"receiver_deployment_hash={tx_hash} gas_estimate={gas_estimate}", flush=True)
    sent = w3.eth.send_raw_transaction(signed.raw_transaction)
    if w3.to_hex(sent).lower() != tx_hash.lower():
        raise RuntimeError("Broadcast hash mismatch")
    receipt = w3.eth.wait_for_transaction_receipt(sent, timeout=120)
    if receipt.status != 1 or not receipt.contractAddress:
        raise RuntimeError("Receiver deployment did not succeed; inspect journal")
    runtime = w3.eth.get_code(receipt.contractAddress)
    if runtime != EXPECTED_RUNTIME:
        raise RuntimeError("Receiver runtime differs from expected REVERT program")
    record = {"network": "bradbury", "chain_id": 4221, "address": receipt.contractAddress,
              "evm_transaction_hash": tx_hash, "deployer": signer.address,
              "creation_sha256": hashlib.sha256(creation).hexdigest(),
              "runtime_hex": w3.to_hex(runtime), "receipt_status": receipt.status,
              "block_number": receipt.blockNumber, "gas_used": receipt.gasUsed,
              "deployed_at": datetime.now(timezone.utc).isoformat()}
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    JOURNAL.unlink()
    print(f"rejecting_receiver={receipt.contractAddress} gas_used={receipt.gasUsed}", flush=True)


if __name__ == "__main__":
    main()
