"""Reconstruct and verify the v0.3 StudioNet demo from finalized chain state."""
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
DEPLOYMENT = json.loads((ROOT / "deployments" / "studionet_v0.3.json").read_text(encoding="utf-8"))
JOURNAL = json.loads((ROOT / ".local" / "demo-state-v0.3.json").read_text(encoding="utf-8"))
OUTPUT = ROOT / "public" / "verification.json"
PROJECT = "MB-LIVE-002"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    client = create_client(chain=studionet, account=Account.create())
    address = DEPLOYMENT["address"]
    encoded = client.provider.make_request(method="gen_getContractCode", params=[address]).get("result")
    require(isinstance(encoded, str), "Onchain source unavailable")
    source = base64.b64decode(encoded, validate=True).decode("utf-8")
    require(sha(source.replace("\r\n", "\n")) == DEPLOYMENT["source_sha256"], "Onchain source differs from release")

    def read(method, args):
        return client.read_contract(address=address, function_name=method, args=args, transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)

    config = read("get_config", [])
    require(config.get("version") == "milestonebond.v0.3" and config.get("delivery_policy") == "SPONSOR_APPROVED_UNMERGED_COMMIT", "Onchain policy mismatch")
    project = read("get_project", [PROJECT])
    require(project["status"] == "COMPLETE" and len(project["milestones"]) == 2, "Two-stage demo is not complete")
    stages = []
    for stage in project["milestones"]:
        require(stage["status"] == "ACCEPTED" and stage["settled_at"] > 0 and len(stage["reviews"]) >= 1, "Stage was not paid")
        review = stage["reviews"][-1]
        captured = review["evidence"]
        require(review["sponsor_approved_at"] > 0 and review["sponsor_approved_at"] <= review["finalized_at"], "Sponsor approval missing")
        require(review["outcome"] == "ACCEPTED" and review["finalized_at"] > 0, "Review not finally accepted")
        require(sha(canonical(captured)) == review["evidence_hash"], "Captured evidence hash mismatch")
        require(captured["author_wallet"] == project["author"] and captured["author_github_id"] == project["author_github_id"], "Author identity mismatch")
        require(captured["claim"] == f"MilestoneBond-Claim: {PROJECT} {project['author']} {review['head_sha']}", "PR claim mismatch")
        require(stage["opened_at"] <= captured["ci"]["started_at"] <= review["submitted_at"], "CI outside stage window")
        require(len(review["checks"]) == len(stage["criteria"]) and all(item["status"] == "SUPPORTED" and item["quote"] for item in review["checks"]), "Criterion proof incomplete")
        for proof in [captured["workflow"], *[p for f in captured["files"] for p in (f["before"], f["after"])]]:
            require(sha(proof["text"]) == proof["sha256"] and len(proof["text"].encode("utf-8")) == proof["bytes"], "Source proof mismatch")
        for item in review["checks"]:
            require(any(item["quote"] in f["after"]["text"] for f in captured["files"]), "Assessment quote absent from source")
        stages.append({"index": stage["index"], "status": stage["status"], "amount_atto": stage["amount"],
                       "pr_url": f"https://github.com/{project['repo']}/pull/{review['pr_number']}",
                       "head_sha": review["head_sha"], "ci_run_id": review["run_id"], "ci_attempt": review["attempt"],
                       "ci_url": f"https://github.com/{project['repo']}/actions/runs/{review['run_id']}/attempts/{review['attempt']}",
                       "evidence_sha256": review["evidence_hash"], "sponsor_approved_at": review["sponsor_approved_at"],
                       "outcome": review["outcome"], "checks": review["checks"], "finalized_at": review["finalized_at"]})

    accounting = read("get_accounting", [project["author"]])
    require(int(accounting["deposited"]) == int(accounting["locked"]) + int(accounting["credited"]) + int(accounting["pending_out"]) + int(accounting["withdrawn"]), "Escrow accounting invariant failed")
    require(int(accounting["locked"]) == 0 and int(accounting["credited"]) == 0 and int(accounting["pending_out"]) == 0 and int(accounting["withdrawn"]) == 2 * 10**15 and accounting["pending_withdrawal"] is None, "Final withdrawal not reconciled")

    transactions = []
    transfer = None
    for item in JOURNAL["transactions"]:
        receipt = client.get_transaction(transaction_hash=item["hash"])
        success = tx_execution_succeeded(receipt)
        require(receipt.get("status_name") == "FINALIZED" and success is not bool(item.get("expected_failure", False)), f"Unexpected {item['method']} execution result")
        require(str(receipt.get("to_address", "")).lower() == address.lower(), "Transaction targeted another contract")
        consensus = receipt.get("consensus_data") or {}
        votes = consensus.get("votes", {})
        error = None
        if item.get("expected_failure"):
            leaders = consensus.get("leader_receipt") or consensus.get("leaderReceipt") or []
            leader = next((entry for entry in leaders if entry.get("mode") == "leader"), None)
            error = (leader or {}).get("result", {}).get("payload")
            if item["method"] == "review_milestone":
                require(isinstance(error, str) and "Sponsor has not approved exact delivery" in error, "Wrong approval-gate failure")
            elif item["method"] == "reconcile_withdrawal":
                require(isinstance(error, str) and "Withdrawal parent mismatch" in error, "Wrong reconciliation failure")
        transactions.append({"method": item["method"], "role": item["role"], "hash": item["hash"],
                             "url": f"https://explorer-studio.genlayer.com/transactions/{item['hash']}",
                             "status": "FINALIZED", "execution_success": success,
                             "expected_failure": bool(item.get("expected_failure", False)), "error": error,
                             "validator_votes": votes})
        if item["method"] == "withdraw":
            children = receipt.get("triggered_transactions", [])
            require(len(children) == 1, "Withdrawal must emit exactly one native transfer")
            child = client.get_transaction(transaction_hash=children[0])
            require(child.get("status_name") == "FINALIZED" and child.get("value_credited") is True, "Child transfer did not credit")
            require(str(child.get("triggered_by", "")).lower() == item["hash"].lower() and str(child.get("from_address", "")).lower() == address.lower() and str(child.get("to_address", "")).lower() == project["author"] and int(child.get("value", 0)) == 2 * 10**15, "Wrong native transfer")
            transfer = {"hash": children[0], "url": f"https://explorer-studio.genlayer.com/transactions/{children[0]}",
                        "parent": item["hash"], "to": project["author"], "value_atto": str(child["value"]), "value_credited": True}
    require(transfer is not None and len([x for x in transactions if x["method"] == "withdraw" and x["execution_success"]]) == 1 and len([x for x in transactions if x["method"] == "reconcile_withdrawal" and x["execution_success"]]) == 1, "Withdrawal lifecycle incomplete")

    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "network": "StudioNet", "chain_id": 61999,
              "scope": "Public sandbox execution with simulated GEN; not a security audit or real-value payout proof",
              "repository": "https://github.com/Demigodd00/milestonebond", "app_url": "https://demigodd00.github.io/milestonebond/",
              "contract": address, "contract_url": f"https://explorer-studio.genlayer.com/contracts/{address}",
              "deployment_hash": DEPLOYMENT["transaction_hash"], "source_sha256": DEPLOYMENT["source_sha256"],
              "source_verified": True, "config": config, "project_id": PROJECT, "project_status": project["status"],
              "issue_url": f"https://github.com/{project['repo']}/issues/{project['issue_number']}",
              "author": project["author"], "author_github_login": project["author_github_login"],
              "author_github_id": project["author_github_id"], "sponsor": project["sponsor"],
              "stages": stages, "accounting": accounting, "transactions": transactions, "outbound_transfer": transfer,
              "limitations": ["Direct adversarial tests use mocked public evidence and receipts; listed StudioNet receipts are the live execution evidence.",
                              "The delivery policy is a sponsor-approved unmerged commit, not proof of merge or independent human identity.",
                              "GitHub, CI and StudioNet RPC remain external trust dependencies; this happy-path transfer does not simulate a failed protocol child.",
                              "Ambiguous transfers remain pending; recovery after a finalized failed child requires real balance coverage, possibly via a donor top-up."]}
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"verified={PROJECT} status={project['status']} contract={address} output={OUTPUT}")


if __name__ == "__main__":
    main()
