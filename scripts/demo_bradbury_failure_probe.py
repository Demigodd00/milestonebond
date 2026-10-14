"""One-shot live Bradbury external-failure probe using the funded demo signer.

Commands: deploy, trigger, inspect. Each phase journals its GenLayer tx ID,
then never auto-retries a submission. No private key is printed or committed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import testnet_bradbury
from genlayer_py.types import TransactionStatus
from web3 import Web3

from bradbury_read import read_final

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "contracts" / "bradbury_transfer_probe.py"
RECEIVER = ROOT / "deployments" / "bradbury_rejecting_receiver.json"
JOURNAL = ROOT / ".local" / "bradbury_failure_probe.json"
RECORD = ROOT / "deployments" / "bradbury_failure_probe.json"
AMOUNT = 10**15  # 0.001 GEN
EXTERNAL_FAILURE_SOURCE = "0x27872802226532FCd7feA2f00AddBFFbd3380Ade"
EXTERNAL_FAILURE_TOPIC = "0x5ae8e754fbc8b7b56c89e264bdcd8bb847036b23ac1a0f791f48b62438f2bab9"


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def context():
    key = json.loads((ROOT / ".local" / "demo-accounts.json").read_text(encoding="utf-8"))["sponsor"]
    account = Account.from_key(key)
    if account.address.lower() != "0x0bcbcde568096ea2c93e71d5f33acd45be00590e":
        raise RuntimeError("Unexpected funded signer")
    client = create_client(chain=testnet_bradbury, account=account)
    if client.w3.eth.chain_id != 4221:
        raise RuntimeError("Wrong chain")
    return account, client


def read_journal() -> dict:
    return json.loads(JOURNAL.read_text(encoding="utf-8")) if JOURNAL.exists() else {"network": "bradbury"}


def finalized(client, txid: str) -> dict:
    receipt = client.wait_for_transaction_receipt(transaction_hash=txid,
                                                  status=TransactionStatus.FINALIZED,
                                                  interval=3000, retries=160,
                                                  full_transaction=True)
    if receipt.get("status_name") != "FINALIZED" or not tx_execution_succeeded(receipt):
        raise RuntimeError(f"Tx finalized without success; inspect {txid}: {str(receipt)[:1000]}")
    return receipt


def deploy() -> None:
    record = read_journal()
    if "deploy" in record:
        raise RuntimeError("Deployment already journaled; use inspect")
    account, client = context()
    source = SOURCE.read_text(encoding="utf-8")
    txid = str(client.deploy_contract(code=source, account=account, args=[]))
    record["deploy"] = {"txid": txid, "source_sha256": hashlib.sha256(source.encode()).hexdigest()}
    save(JOURNAL, record)
    print(f"probe_deploy_txid={txid}", flush=True)
    receipt = finalized(client, txid)
    address = (receipt.get("tx_data_decoded") or {}).get("contract_address")
    if not address:
        print(f"finalized_receipt={str(receipt)[:2500]}", flush=True)
        raise RuntimeError("Cannot extract probe contract address")
    record["deploy"].update({"address": address, "finalized": True})
    save(JOURNAL, record)
    print(f"probe_address={address}", flush=True)


def recover_deploy() -> None:
    record = read_journal()
    deployment = record.get("deploy") or {}
    if not deployment.get("txid") or deployment.get("address"):
        raise RuntimeError("No pending deployment to recover")
    _, client = context()
    raw = client.w3.provider.make_request("gen_getTransactionReceipt",
                                          [{"txId": deployment["txid"]}])
    receipt = raw.get("result") or {}
    if receipt.get("status") != 7 or receipt.get("txExecutionResult") != 1:
        raise RuntimeError("Deployment has not finalized successfully")
    # On Bradbury the deploy receipt recipient is the new ghost/IC address.
    address = receipt.get("recipient")
    if not address or len(address) != 42:
        raise RuntimeError(f"No contract address in finalized receipt: {str(receipt)[:1500]}")
    source = SOURCE.read_text(encoding="utf-8")
    code = client.provider.make_request("gen_getContractCode", [{"address": address,
                                                               "status": "finalized"}]).get("result")
    import base64
    if not isinstance(code, str) or base64.b64decode(code, validate=True).decode("utf-8") != source:
        raise RuntimeError("Deployed probe source cannot be verified")
    deployment.update({"address": address, "finalized": True})
    save(JOURNAL, record)
    print(f"probe_address={address}", flush=True)


def trigger() -> None:
    record = read_journal()
    if "trigger" in record:
        raise RuntimeError("Trigger already journaled; use inspect")
    address = record.get("deploy", {}).get("address")
    if not address:
        raise RuntimeError("Probe deployment not verified")
    receiver = json.loads(RECEIVER.read_text(encoding="utf-8"))["address"]
    account, client = context()
    address = client.w3.to_checksum_address(address)
    before = client.w3.eth.get_balance(address)
    txid = str(client.write_contract(address=address, function_name="trigger",
                                     args=[receiver], account=account, value=AMOUNT))
    record["trigger"] = {"txid": txid, "recipient": receiver, "amount": AMOUNT,
                         "balance_before": before}
    save(JOURNAL, record)
    print(f"probe_trigger_txid={txid}", flush=True)
    finalized(client, txid)
    print("trigger_finalized_successfully; inspect EVM finalization now", flush=True)


def inspect() -> None:
    record = read_journal()
    txid = record.get("trigger", {}).get("txid")
    address = record.get("deploy", {}).get("address")
    if not txid or not address:
        raise RuntimeError("Deploy and trigger first")
    account, client = context()
    address = client.w3.to_checksum_address(address)
    w3 = client.w3
    transaction = w3.provider.make_request("gen_getTransactionReceipt", [{"txId": txid}]).get("result") or {}
    if transaction.get("status") != 7 or transaction.get("txExecutionResult") != 1:
        raise RuntimeError("Trigger is not finalized with successful execution")
    data_contract = w3.eth.contract(address=testnet_bradbury.consensus_data_contract["address"],
                                    abi=testnet_bradbury.consensus_data_contract["abi"])
    tx_data = data_contract.functions.getTransactionData(txid, int(datetime.now(timezone.utc).timestamp())).call()
    messages = tx_data[12]
    if len(messages) != 1:
        raise RuntimeError("Expected exactly one external message")
    topic = w3.keccak(text="TransactionFinalized(bytes32)").hex()
    latest = w3.eth.block_number
    proposal = transaction.get("readStateBlockRanges", [{}])[0].get("ProposalBlock", latest - 10000)
    logs = w3.eth.get_logs({"fromBlock": max(int(proposal), latest - 10000),
                            "toBlock": latest,
                            "address": testnet_bradbury.consensus_main_contract["address"],
                            "topics": [topic, txid]})
    if len(logs) != 1:
        raise RuntimeError(f"Expected one finalization log; got {len(logs)}")
    evm_hash = w3.to_hex(logs[0]["transactionHash"])
    evm_receipt = w3.eth.get_transaction_receipt(evm_hash)
    # Topic-only parsing avoids warnings from unrelated logs in the same batch.
    fail_topic = w3.to_hex(w3.keccak(text="ValueWithdrawalFailed(bytes32,address,uint256)"))
    failed_logs = [item for item in evm_receipt["logs"]
                   if item["address"].lower() == testnet_bradbury.consensus_main_contract["address"].lower()
                   and w3.to_hex(item["topics"][0]).lower() == fail_topic.lower()
                   and len(item["topics"]) == 3
                   and w3.to_hex(item["topics"][1]).lower() == txid.lower()]
    receiver = record["trigger"]["recipient"]
    failed_exactly = (len(failed_logs) == 1
                      and w3.to_hex(failed_logs[0]["topics"][2]).lower()
                      == "0x" + receiver[2:].lower().rjust(64, "0")
                      and int.from_bytes(failed_logs[0]["data"], "big") == AMOUNT)
    # The live Bradbury deployment reports the ghost handleOp rejection from
    # its message-processing contract, rather than ValueWithdrawalFailed.
    # Bind that exact log to the one finalized external message, and report
    # the two event families separately so reviewers can inspect the raw logs.
    protocol_failures = [item for item in evm_receipt["logs"]
                         if item["address"].lower() == EXTERNAL_FAILURE_SOURCE.lower()
                         and len(item["topics"]) == 3
                         and w3.to_hex(item["topics"][0]).lower() == EXTERNAL_FAILURE_TOPIC
                         and w3.to_hex(item["topics"][1]).lower() == txid.lower()]
    external_failure_exact = (len(protocol_failures) == 1
                              and messages[0][0] == 0
                              and str(messages[0][1]).lower() == receiver.lower()
                              and messages[0][2] == AMOUNT
                              and messages[0][3] == b""
                              and messages[0][4] is False
                              and int.from_bytes(protocol_failures[0]["data"][:32], "big") == 32
                              and int.from_bytes(protocol_failures[0]["data"][32:64], "big") == 20
                              and protocol_failures[0]["data"][64:84] == b"handleOp call failed"
                              and w3.eth.get_balance(address) == record["trigger"]["balance_before"] + AMOUNT
                              and w3.eth.get_balance(receiver) == 0)
    # Bradbury's current gen_call may return an error object where this SDK
    # expects an encoded string. It is auxiliary; finalized receipts, event
    # identity and EVM balances below are the decisive transfer evidence.
    try:
        state = read_final(client, address, account.address, "state", [])
        state_error = None
    except (TypeError, ValueError) as exc:
        state = None
        state_error = f"Optional SDK state read unavailable: {type(exc).__name__}"
    evidence = {"network": "bradbury", "chain_id": 4221,
                "probe_address": address, "receiver": record["trigger"]["recipient"],
                "transfer_amount": AMOUNT, "genlayer_transaction_id": txid,
                "evm_finalization_hash": evm_hash, "evm_receipt_status": evm_receipt.status,
                "finalization_block": evm_receipt.blockNumber,
                "message": [str(field) for field in messages[0]],
                "failure_events": [{"recipient_topic": w3.to_hex(item["topics"][2]),
                                    "value_hex": w3.to_hex(item["data"]),
                                    "log_index": item["logIndex"]} for item in failed_logs],
                "exact_failure_event_verified": failed_exactly,
                "protocol_failure_logs": [{"source": item["address"],
                                           "topic0": w3.to_hex(item["topics"][0]),
                                           "message_hash": w3.to_hex(item["topics"][2]),
                                           "log_index": item["logIndex"]}
                                          for item in protocol_failures],
                "exact_external_failure_verified": external_failure_exact,
                "balance_before": record["trigger"]["balance_before"],
                "balance_after": w3.eth.get_balance(address),
                "receiver_balance": w3.eth.get_balance(record["trigger"]["recipient"]),
                "genvm_state": state, "genvm_state_read_error": state_error,
                "inspected_at": datetime.now(timezone.utc).isoformat()}
    save(RECORD, evidence)
    print(json.dumps(evidence, indent=2), flush=True)


if __name__ == "__main__":
    {"deploy": deploy, "recover-deploy": recover_deploy,
     "trigger": trigger, "inspect": inspect}[sys.argv[1]]()
