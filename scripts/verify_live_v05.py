"""Build public v0.5 proof only after all four Bradbury actions finalize.

This verifier re-reads source, policy, transactions, the EVM failure receipt,
the one external message and final accounting. It never submits a transaction.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from genlayer_py import create_client
from genlayer_py.chains import testnet_bradbury
from web3 import Web3

from bradbury_read import read_final
from build_compact_v05 import READABLE, DEPLOYABLE as COMPACT, compact
from build_packed_v05 import PACKED, pack

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = ROOT / "deployments" / "bradbury_v0.5.json"
RECEIVER = ROOT / "deployments" / "bradbury_rejecting_receiver.json"
JOURNAL = ROOT / ".local" / "bradbury-v05-demo.json"
OUTPUT = ROOT / "public" / "verification-v0.5.json"
AMOUNT = 2 * 10**15
METHODS = ("create_project", "recover_expired", "withdraw_to", "reconcile_withdrawal")
PROCESSOR = "0x27872802226532FCd7feA2f00AddBFFbd3380Ade"
PROCESSOR_FAILURE_TOPIC = "0x5ae8e754fbc8b7b56c89e264bdcd8bb847036b23ac1a0f791f48b62438f2bab9"
SETTLEMENT_TOPIC = "0x6565c26927b368d6e75314c8bf1c1e2847f1cdd47b89e10ae002a2889da4d150"
FINALIZED_TOPIC = "0x24196ec40f90671b7144e716978686b4f3c7d6b00b23da3971ef2b52af27d87f"
FAILED_TOPIC = "0xd7d0ee861c0ebf42599b922e8f4ad0cafed951841610157bcd56110f49ced8ee"


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    deployment = json.loads(DEPLOYMENT.read_text(encoding="utf-8"))
    journal = json.loads(JOURNAL.read_text(encoding="utf-8"))
    receiver_record = json.loads(RECEIVER.read_text(encoding="utf-8"))
    transactions = journal.get("transactions", [])
    require(tuple(item["method"] for item in transactions) == METHODS, "Incomplete v0.5 action sequence")
    require(deployment.get("verified_source_and_config") is True and deployment.get("chain_id") == 4221,
            "Bradbury deployment not verified")
    source = PACKED.read_text(encoding="utf-8")
    readable = READABLE.read_text(encoding="utf-8")
    compact_source = COMPACT.read_text(encoding="utf-8")
    require(compact_source == compact(readable) and source == pack(compact_source),
            "Deployment wrapper is not reproducibly bound to the readable source")
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    require(source_hash == deployment["source_sha256"], "Local deployed-source hash changed")

    client = create_client(chain=testnet_bradbury)
    w3 = client.w3
    require(w3.eth.chain_id == 4221, "Wrong EVM network")
    address, sponsor = deployment["address"], deployment["deployer"]
    receiver = receiver_record["address"]
    main_address = testnet_bradbury.consensus_main_contract["address"]
    encoded = client.provider.make_request("gen_getContractCode", [
        {"address": address, "status": "finalized"}]).get("result")
    require(isinstance(encoded, str) and base64.b64decode(encoded, validate=True).decode("utf-8") == source,
            "Finalized deployed source differs from the packed artifact")
    require(w3.eth.get_code(receiver) == bytes.fromhex("60006000fd"), "Rejecting receiver runtime changed")
    config = read_final(client, address, sponsor, "get_config", [])
    require(config == deployment["deployed_config"] and config["version"] == "milestonebond.v0.5",
            "Finalized policy changed")

    finalized = []
    for item in transactions:
        raw = client.provider.make_request("gen_getTransactionReceipt", [
            {"txId": item["txid"]}]).get("result") or {}
        require(raw.get("status") == 7 and raw.get("txExecutionResult") == 1
                and str(raw.get("recipient", "")).lower() == address.lower(),
                f"{item['method']} lacks finalized successful execution")
        finalized.append({"method": item["method"], "hash": item["txid"],
                          "url": "https://explorer-bradbury.genlayer.com/tx/" + item["txid"],
                          "status": "FINALIZED", "execution_success": True})

    failure = journal.get("failure_evidence") or {}
    withdrawal_id = transactions[2]["txid"]
    evm_hash = failure.get("evm_finalization_hash")
    require(failure.get("genlayer_transaction_id") == withdrawal_id and isinstance(evm_hash, str),
            "Missing exact live failure evidence")
    evm = w3.eth.get_transaction_receipt(evm_hash)
    require(evm.status == 1 and evm.to.lower() == main_address.lower(), "Invalid EVM finalization")
    logs = list(evm.logs)
    matching = lambda source, topic, count: [log for log in logs
        if log.address.lower() == source.lower() and len(log.topics) == count
        and w3.to_hex(log.topics[0]).lower() == topic
        and w3.to_hex(log.topics[1]).lower() == withdrawal_id.lower()]
    require(len(matching(main_address, FINALIZED_TOPIC, 2)) == 1, "Wrong finalization transaction")
    failed = matching(main_address, FAILED_TOPIC, 3)
    processor = matching(PROCESSOR, PROCESSOR_FAILURE_TOPIC, 3)
    require(len(failed) + len(processor) == 1, "External rejection not unambiguous")
    if processor:
        reason = b"handleOp call failed"
        data = (32).to_bytes(32, "big") + len(reason).to_bytes(32, "big") + reason.ljust(32, b"\0")
        settlement = matching(main_address, SETTLEMENT_TOPIC, 2)
        require(processor[0].data == data and int.from_bytes(processor[0].topics[2], "big") != 0
                and len(settlement) == 1
                and settlement[0].data == AMOUNT.to_bytes(32, "big") + (1).to_bytes(32, "big"),
                "Message processor rejection or settlement amount mismatch")
        family = "MessageProcessorFailure"
    else:
        target = "0x" + receiver[2:].lower().rjust(64, "0")
        require(w3.to_hex(failed[0].topics[2]).lower() == target
                and int.from_bytes(failed[0].data, "big") == AMOUNT,
                "Value withdrawal rejection recipient/amount mismatch")
        family = "ValueWithdrawalFailed"
    require(failure.get("failure_event_family") == family, "Journaled failure family changed")
    data_contract = w3.eth.contract(address=testnet_bradbury.consensus_data_contract["address"],
                                    abi=testnet_bradbury.consensus_data_contract["abi"])
    messages = data_contract.functions.getTransactionData(withdrawal_id,
        int(datetime.now(timezone.utc).timestamp())).call()[12]
    require(len(messages) == 1 and messages[0][0] == 0
            and str(messages[0][1]).lower() == receiver.lower() and messages[0][2] == AMOUNT
            and messages[0][3] == b"" and messages[0][4] is False,
            "External message not bound to the rejecting receiver and amount")
    require(w3.eth.get_balance(receiver) == failure.get("receiver_balance_before")
            == failure.get("receiver_balance_after"), "Receiver received value")
    require(failure.get("contract_balance_before") == failure.get("contract_balance_after"),
            "The failed transfer was not returned")

    project_id = journal["project"]
    project = read_final(client, address, sponsor, "get_project", [project_id])
    accounting = read_final(client, address, sponsor, "get_accounting", [sponsor])
    credit = read_final(client, address, sponsor, "get_project_accounting", [project_id, sponsor])
    require(project["status"] == "REFUNDED" and project["sponsor"].lower() == sponsor.lower()
            and project["reserve_initial"] == str(AMOUNT)
            and project["reserve_remaining"] == str(AMOUNT)
            and project["reserve_consumed"] == "0" and project["claims_outstanding"] == str(AMOUNT),
            "Project reserve or entitlement state mismatch")
    require(credit["claimable"] == str(AMOUNT) and accounting["claimable"] == str(AMOUNT)
            and accounting["pending_withdrawal"] is None and accounting["pending_out"] == "0"
            and accounting["credited"] == str(AMOUNT) and accounting["withdrawn"] == "0"
            and accounting["reserve_locked"] == str(AMOUNT)
            and accounting["contract_balance"] == str(2 * AMOUNT),
            "Recovery entitlement or no-duplicate-payout invariant mismatch")
    require(w3.eth.get_balance(Web3.to_checksum_address(address)) == 2 * AMOUNT,
            "Ghost EVM balance contradicts finalized GenLayer accounting")

    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "network": "Bradbury testnet", "chain_id": 4221,
              "scope": "Finalized external rejection and restored test-GEN entitlement; not production insurance",
              "repository": "https://github.com/Demigodd00/milestonebond",
              "app_url": "https://demigodd00.github.io/milestonebond/",
              "contract": address,
              "contract_url": "https://explorer-bradbury.genlayer.com/address/" + address,
              "deployment_hash": deployment["transaction_id"],
              "source_sha256": source_hash,
              "readable_source_sha256": hashlib.sha256(readable.encode("utf-8")).hexdigest(),
              "source_verified": True, "config": config,
              "project_id": project_id, "project": project,
              "project_accounting": credit, "accounting": accounting,
              "receiver": receiver, "receiver_runtime": "0x60006000fd",
              "failure": failure, "transactions": finalized,
              "limitations": ["Finite sponsor-funded reserve, not unlimited recovery",
                              "A failed transfer restored credit but did not itself pay the sponsor",
                              "The finalization and RPC logs are Bradbury testnet evidence only"]}
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"verified_v05={address} recovery={credit['claimable']} transactions={len(finalized)}", flush=True)


if __name__ == "__main__":
    main()
