"""Permissionlessly finalize a ready Bradbury GenLayer transaction once.

Usage: python scripts/finalize_bradbury.py 0x<64-hex GenLayer transaction ID>
Only runs after onchain canFinalize is true; journals the signed EVM hash before
broadcast and never retries an existing journaled transaction.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from eth_account import Account
from genlayer_py.chains import testnet_bradbury
from web3 import Web3

ROOT = Path(__file__).resolve().parents[1]


def main(txid: str) -> None:
    if re.fullmatch(r"0x[0-9a-fA-F]{64}", txid) is None:
        raise RuntimeError("Supply a full GenLayer transaction ID")
    txid = txid.lower()
    journal = ROOT / ".local" / "finalizations" / (txid[2:] + ".json")
    if journal.exists():
        raise RuntimeError("Finalization already journaled; inspect its EVM hash, do not repeat")
    key = json.loads((ROOT / ".local" / "demo-accounts.json").read_text(encoding="utf-8"))["sponsor"]
    signer = Account.from_key(key)
    if signer.address.lower() != "0x0bcbcde568096ea2c93e71d5f33acd45be00590e":
        raise RuntimeError("Unexpected funded test signer")
    w3 = Web3(Web3.HTTPProvider("https://rpc.testnet-chain.genlayer.com",
                               request_kwargs={"timeout": 25}))
    if w3.eth.chain_id != 4221:
        raise RuntimeError("Wrong chain")
    chain = testnet_bradbury
    main_contract = w3.eth.contract(address=chain.consensus_main_contract["address"],
                                    abi=chain.consensus_main_contract["abi"])
    data_contract = w3.eth.contract(address=chain.consensus_data_contract["address"],
                                    abi=chain.consensus_data_contract["abi"])
    ready = data_contract.functions.canFinalize(txid, int(time.time())).call()
    if not ready[0]:
        print(f"not_finalizable_yet deadline={ready[2]}", flush=True)
        return
    call = main_contract.functions.finalizeTransaction(txid)
    data = call._encode_transaction_data()
    estimate = w3.eth.estimate_gas({"from": signer.address,
                                    "to": chain.consensus_main_contract["address"],
                                    "data": data})
    gas_limit = (estimate * 12 + 9) // 10
    base = w3.eth.get_block("latest")["baseFeePerGas"]
    maximum_fee = base + w3.to_wei(2, "gwei")
    if gas_limit * maximum_fee > w3.to_wei(0.1, "ether"):
        raise RuntimeError("Estimated maximum exceeds 0.1 GEN safety cap")
    nonce = w3.eth.get_transaction_count(signer.address)
    signed = signer.sign_transaction({"from": signer.address, "to": chain.consensus_main_contract["address"],
                                      "nonce": nonce, "chainId": 4221, "value": 0,
                                      "data": data, "gas": gas_limit,
                                      "maxFeePerGas": maximum_fee,
                                      "maxPriorityFeePerGas": w3.to_wei(2, "gwei")})
    evm_hash = w3.to_hex(signed.hash)
    journal.parent.mkdir(exist_ok=True)
    journal.write_text(json.dumps({"genlayer_transaction_id": txid,
                                   "evm_finalization_hash": evm_hash,
                                   "gas_estimate": estimate, "nonce": nonce}, indent=2) + "\n",
                       encoding="utf-8")
    print(f"finalization_evm_hash={evm_hash} gas_estimate={estimate}", flush=True)
    sent = w3.eth.send_raw_transaction(signed.raw_transaction)
    if w3.to_hex(sent).lower() != evm_hash.lower():
        raise RuntimeError("Broadcast hash mismatch")
    receipt = w3.eth.wait_for_transaction_receipt(sent, timeout=120)
    if receipt.status != 1:
        raise RuntimeError("Finalization EVM transaction reverted; inspect journal")
    events = main_contract.events.TransactionFinalized().process_receipt(receipt)
    if not any(w3.to_hex(event["args"]["txId"]).lower() == txid for event in events):
        raise RuntimeError("No matching finalization event in successful receipt")
    print(f"finalized_txid={txid} block={receipt.blockNumber} gas_used={receipt.gasUsed}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
