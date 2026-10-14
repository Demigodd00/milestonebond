"""One-shot live MilestoneBond v0.5 failed-withdrawal lifecycle.

Use distinct commands, checking the journal between submissions. Each command
submits at most one GenLayer transaction, journals its ID, and never retries.
Do not publish a failure claim until the exact EVM finalization log is checked.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.chains import testnet_bradbury
from web3 import Web3

from bradbury_read import read_final

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = ROOT / "deployments" / "bradbury_v0.5.json"
RECEIVER = ROOT / "deployments" / "bradbury_rejecting_receiver.json"
JOURNAL = ROOT / ".local" / "bradbury-v05-demo.json"
PROJECT = "MB-BRADBURY-FAIL-001"
REQUEST = "7" * 64
AMOUNT = 2 * 10**15
PROCESSOR = "0x27872802226532FCd7feA2f00AddBFFbd3380Ade"
PROCESSOR_FAILURE_TOPIC = "0x5ae8e754fbc8b7b56c89e264bdcd8bb847036b23ac1a0f791f48b62438f2bab9"
SETTLEMENT_TOPIC = "0x6565c26927b368d6e75314c8bf1c1e2847f1cdd47b89e10ae002a2889da4d150"


def save(data: dict) -> None:
    JOURNAL.parent.mkdir(exist_ok=True)
    JOURNAL.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def journal() -> dict:
    return json.loads(JOURNAL.read_text(encoding="utf-8")) if JOURNAL.exists() else {"project": PROJECT, "transactions": []}


def context():
    record = json.loads(DEPLOYMENT.read_text(encoding="utf-8"))
    if record.get("version") != "milestonebond.v0.5" or record.get("chain_id") != 4221:
        raise RuntimeError("Bradbury v0.5 release not verified")
    key = json.loads((ROOT / ".local" / "demo-accounts.json").read_text(encoding="utf-8"))["sponsor"]
    signer = Account.from_key(key)
    if signer.address.lower() != "0x0bcbcde568096ea2c93e71d5f33acd45be00590e":
        raise RuntimeError("Unexpected demo signer")
    client = create_client(chain=testnet_bradbury, account=signer)
    return record["address"], signer, client


def read(method: str, args: list):
    address, signer, client = context()
    return read_final(client, address, signer.address, method, args)


def submit(method: str, args: list, value: int = 0) -> str:
    record = journal()
    if any(item["method"] == method for item in record["transactions"]):
        raise RuntimeError(f"{method} already journaled; inspect before any retry")
    address, signer, client = context()
    if client.w3.eth.chain_id != 4221:
        raise RuntimeError("Wrong chain")
    txid = str(client.write_contract(address=address, function_name=method,
                                     args=args, account=signer, value=value))
    record["transactions"].append({"method": method, "txid": txid,
                                   "value": value, "submitted_at": datetime.now(timezone.utc).isoformat()})
    save(record)
    print(f"submitted_{method}={txid}", flush=True)
    return txid


def receipt(txid: str) -> dict:
    _, _, client = context()
    result = client.w3.provider.make_request("gen_getTransactionReceipt", [{"txId": txid}]).get("result") or {}
    return {"status": result.get("status"), "execution": result.get("txExecutionResult"),
            "recipient": result.get("recipient"), "sender": result.get("sender"),
            "proposal_block": (result.get("readStateBlockRanges") or [{}])[0].get("ProposalBlock")}


def require_final(method: str) -> str:
    item = next((item for item in journal()["transactions"] if item["method"] == method), None)
    if not item:
        raise RuntimeError(f"{method} not submitted")
    state = receipt(item["txid"])
    if state["status"] != 7 or state["execution"] != 1:
        raise RuntimeError(f"{method} not finalized with successful execution: {state}")
    return item["txid"]


def fund() -> None:
    from demo_operator import terms
    _, signer, _ = context()
    author_key = json.loads((ROOT / ".local" / "demo-accounts.json").read_text(encoding="utf-8"))["author"]
    author = Account.from_key(author_key).address
    fixed = terms(author)
    fixed["id"] = PROJECT
    fixed["title"] = "Live Bradbury failed withdrawal and reserve reconciliation fixture"
    fixed["accept_by"] = int(datetime.now(timezone.utc).timestamp()) + 900
    if author.lower() == signer.address.lower():
        raise RuntimeError("Fixture author must differ from sponsor")
    submit("create_project", [json.dumps(fixed)], 2 * AMOUNT)


def recover() -> None:
    require_final("create_project")
    project = read("get_project", [PROJECT])
    if project["status"] != "AWAITING_AUTHOR" or int(datetime.now(timezone.utc).timestamp()) < project["accept_by"]:
        raise RuntimeError("Acceptance deadline has not passed")
    submit("recover_expired", [PROJECT])


def withdraw() -> None:
    require_final("recover_expired")
    address, signer, _ = context()
    project = read("get_project", [PROJECT])
    account = read("get_project_accounting", [PROJECT, signer.address])
    if project["status"] != "REFUNDED" or account["claimable"] != str(AMOUNT):
        raise RuntimeError("Refunded project credit missing")
    recipient = json.loads(RECEIVER.read_text(encoding="utf-8"))["address"]
    _, _, client = context()
    record = journal()
    record["withdrawal_before"] = {
        "contract_balance": client.w3.eth.get_balance(Web3.to_checksum_address(address)),
        "receiver_balance": client.w3.eth.get_balance(recipient),
    }
    save(record)
    submit("withdraw_to", [PROJECT, REQUEST, recipient])


def failure_evidence() -> dict:
    txid = require_final("withdraw_to")
    address, signer, client = context()
    receiver = json.loads(RECEIVER.read_text(encoding="utf-8"))["address"]
    latest = client.w3.eth.block_number
    proposal = receipt(txid)["proposal_block"]
    if proposal is None:
        raise RuntimeError("Finalized receipt has no proposal block for the EVM log search")
    start = int(proposal)
    main = testnet_bradbury.consensus_main_contract["address"]
    final_topic = client.w3.keccak(text="TransactionFinalized(bytes32)").hex()
    logs = []
    for first in range(start, latest + 1, 5000):
        logs.extend(client.w3.eth.get_logs({"fromBlock": first, "toBlock": min(first + 4999, latest),
                                            "address": main, "topics": [final_topic, txid]}))
    if len(logs) != 1:
        raise RuntimeError("Missing or ambiguous EVM finalization")
    evm_hash = client.w3.to_hex(logs[0]["transactionHash"])
    evm = client.w3.eth.get_transaction_receipt(evm_hash)
    if evm.status != 1 or evm.to.lower() != main.lower():
        raise RuntimeError("EVM finalization receipt is not a successful main-contract call")
    data_contract = client.w3.eth.contract(address=testnet_bradbury.consensus_data_contract["address"],
                                           abi=testnet_bradbury.consensus_data_contract["abi"])
    transaction = data_contract.functions.getTransactionData(
        txid, int(datetime.now(timezone.utc).timestamp())).call()
    messages = transaction[12]
    if len(messages) != 1 or messages[0][0] != 0 or str(messages[0][1]).lower() != receiver.lower() \
            or messages[0][2] != AMOUNT or messages[0][3] != b"" or messages[0][4] is not False:
        raise RuntimeError("Finalized transaction has no exact single external transfer")
    fail_topic = client.w3.keccak(text="ValueWithdrawalFailed(bytes32,address,uint256)").hex()
    failed = [log for log in evm["logs"] if log["address"].lower() == main.lower()
              and len(log["topics"]) == 3
              and client.w3.to_hex(log["topics"][0]).lower() == "0x" + fail_topic.lower().removeprefix("0x")
              and client.w3.to_hex(log["topics"][1]).lower() == txid.lower()]
    protocol_failures = [log for log in evm["logs"] if log["address"].lower() == PROCESSOR.lower()
                         and len(log["topics"]) == 3
                         and client.w3.to_hex(log["topics"][0]).lower() == PROCESSOR_FAILURE_TOPIC
                         and client.w3.to_hex(log["topics"][1]).lower() == txid.lower()]
    if len(failed) + len(protocol_failures) != 1:
        raise RuntimeError("Expected one unambiguous linked external failure log")
    if failed:
        event = failed[0]
        encoded_receiver = "0x" + receiver[2:].lower().rjust(64, "0")
        if client.w3.to_hex(event["topics"][2]).lower() != encoded_receiver \
                or int.from_bytes(event["data"], "big") != AMOUNT:
            raise RuntimeError("Failed event recipient or value mismatch")
        family = "ValueWithdrawalFailed"
    else:
        event = protocol_failures[0]
        reason = b"handleOp call failed"
        expected_data = (32).to_bytes(32, "big") + len(reason).to_bytes(32, "big") \
            + reason.ljust(32, b"\0")
        settlement = [log for log in evm["logs"] if log["address"].lower() == main.lower()
                      and len(log["topics"]) == 2
                      and client.w3.to_hex(log["topics"][0]).lower() == SETTLEMENT_TOPIC
                      and client.w3.to_hex(log["topics"][1]).lower() == txid.lower()]
        settlement_data = AMOUNT.to_bytes(32, "big") + (1).to_bytes(32, "big")
        if event["data"] != expected_data or int.from_bytes(event["topics"][2], "big") == 0 \
                or len(settlement) != 1 or settlement[0]["data"] != settlement_data:
            raise RuntimeError("Message-processor failure or settlement amount mismatch")
        family = "MessageProcessorFailure"
    pending = read("get_accounting", [signer.address])
    if pending["pending_withdrawal"]["request_id"] != REQUEST:
        raise RuntimeError("Pending request changed")
    record = journal()
    before = record.get("withdrawal_before") or {}
    after_contract = client.w3.eth.get_balance(Web3.to_checksum_address(address))
    after_receiver = client.w3.eth.get_balance(receiver)
    if after_receiver != before.get("receiver_balance") or after_contract != before.get("contract_balance"):
        raise RuntimeError("External rejection did not preserve pre-withdrawal balances")
    record["failure_evidence"] = {"genlayer_transaction_id": txid,
                                  "evm_finalization_hash": evm_hash,
                                  "evm_block": evm.blockNumber,
                                  "evm_receipt_status": evm.status,
                                  "failure_event_family": family,
                                  "failed_event_index": event["logIndex"],
                                  "message": [str(field) for field in messages[0]],
                                  "receiver": receiver, "amount": AMOUNT,
                                  "contract_balance_before": before["contract_balance"],
                                  "contract_balance_after": after_contract,
                                  "receiver_balance_before": before["receiver_balance"],
                                  "receiver_balance_after": after_receiver,
                                  "pending_accounting": pending}
    save(record)
    print(json.dumps(record["failure_evidence"], indent=2), flush=True)
    return record["failure_evidence"]


def reconcile() -> None:
    evidence = failure_evidence()
    submit("reconcile_withdrawal", [evidence["genlayer_transaction_id"],
                                    evidence["evm_finalization_hash"]])


def status() -> None:
    record = journal()
    record["receipts"] = {item["method"]: receipt(item["txid"])
                          for item in record["transactions"]}
    print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("fund", "recover", "withdraw", "failure-evidence", "reconcile", "status"):
        raise SystemExit("Usage: demo_bradbury_v05.py fund|recover|withdraw|failure-evidence|reconcile|status")
    {"fund": fund, "recover": recover, "withdraw": withdraw,
     "failure-evidence": failure_evidence, "reconcile": reconcile,
     "status": status}[sys.argv[1]]()
