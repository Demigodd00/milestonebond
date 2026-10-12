"""Export a read-only public verification record for the StudioNet demo."""
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
DEPLOYMENT = json.loads((ROOT / "deployments" / "studionet.json").read_text(encoding="utf-8"))
JOURNAL = ROOT / ".local" / "demo-state.json"
OUTPUT = ROOT / "public" / "verification.json"


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    client = create_client(chain=studionet, account=Account.create())
    address = DEPLOYMENT["address"]
    encoded = client.provider.make_request(method="gen_getContractCode", params=[address]).get("result")
    if not isinstance(encoded, str):
        raise RuntimeError("Cannot read onchain source")
    source = base64.b64decode(encoded, validate=True).decode("utf-8")
    if digest(source.replace("\r\n", "\n")) != DEPLOYMENT["source_sha256"]:
        raise RuntimeError("Onchain source digest mismatch")
    def read(method, args):
        return client.read_contract(address=address, function_name=method, args=args, transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)
    config = read("get_config", [])
    if config.get("version") != DEPLOYMENT["version"]:
        raise RuntimeError("Onchain version mismatch")
    project = read("get_project", ["MB-LIVE-001"])
    stages = []
    for stage in project["milestones"]:
        reviews = []
        for review in stage["reviews"]:
            captured = review["evidence"]
            if digest(canonical(captured)) != review["evidence_hash"]:
                raise RuntimeError("Onchain evidence digest mismatch")
            for proof in [captured["workflow"], *[p for f in captured["files"] for p in (f["before"], f["after"])]]:
                if digest(proof["text"]) != proof["sha256"] or len(proof["text"].encode("utf-8")) != proof["bytes"]:
                    raise RuntimeError("Onchain source proof mismatch")
            checks = review.get("checks", [])
            if review.get("outcome") == "ACCEPTED" and not (review.get("scope_ok") and len(checks) == len(stage["criteria"]) and all(c["status"] == "SUPPORTED" for c in checks)):
                raise RuntimeError("Accepted outcome lacks complete supported criteria")
            reviews.append({"revision": review["revision"], "pr_number": review["pr_number"], "pr_url": f"https://github.com/{project['repo']}/pull/{review['pr_number']}",
                            "head_sha": review["head_sha"], "ci_run_id": review["run_id"], "ci_attempt": review["attempt"],
                            "ci_url": f"https://github.com/{project['repo']}/actions/runs/{review['run_id']}",
                            "evidence_sha256": review["evidence_hash"], "evidence_digest_verified": True,
                            "outcome": review.get("outcome"), "scope_ok": review.get("scope_ok"), "checks": checks,
                            "challenge_used": review["challenge_used"], "finalized_at": review["finalized_at"]})
        stages.append({"index": stage["index"], "title": stage["title"], "criteria": stage["criteria"], "amount_atto": stage["amount"],
                       "status": stage["status"], "opened_at": stage["opened_at"], "settled_at": stage["settled_at"], "reviews": reviews})
    sponsor = read("get_accounting", [project["sponsor"]])
    author = read("get_accounting", [project["author"]])
    if int(sponsor["deposited"]) != int(sponsor["locked"]) + int(sponsor["credited"]) + int(sponsor["withdrawn"]):
        raise RuntimeError("Escrow accounting invariant failed")
    transactions = []
    transfers = []
    if JOURNAL.exists():
        for item in json.loads(JOURNAL.read_text(encoding="utf-8"))["transactions"]:
            receipt = client.get_transaction(transaction_hash=item["hash"])
            status = receipt.get("status_name") or receipt.get("statusName")
            success = tx_execution_succeeded(receipt)
            consensus = receipt.get("consensus_data") or receipt.get("consensusData") or {}
            votes = consensus.get("votes", {}) if isinstance(consensus, dict) else {}
            transactions.append({"hash": item["hash"], "url": f"https://explorer-studio.genlayer.com/transactions/{item['hash']}",
                                 "method": item["method"], "role": item["role"], "status": status, "execution_success": success,
                                 "on_active_contract": str(receipt.get("to_address", "")).lower() == address.lower(),
                                 "validator_votes": votes})
            if item["method"] == "withdraw" and success:
                for triggered_hash in receipt.get("triggered_transactions", []):
                    transfer = client.get_transaction(transaction_hash=triggered_hash)
                    transfer_status = transfer.get("status_name") or transfer.get("statusName")
                    if transfer_status != "FINALIZED" or str(transfer.get("to_address", "")).lower() != project["author"].lower() or int(transfer.get("value", 0)) != 2 * 10**15 or transfer.get("value_credited") is not True:
                        raise RuntimeError("Outbound test-GEN transfer is not finalized, credited, or exact")
                    transfers.append({"hash": triggered_hash, "url": f"https://explorer-studio.genlayer.com/transactions/{triggered_hash}",
                                      "parent_withdrawal": item["hash"], "status": transfer_status,
                                      "to": transfer.get("to_address"), "value_atto": str(transfer.get("value")),
                                      "value_credited": transfer.get("value_credited")})
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "network": "StudioNet", "chain_id": 61999,
              "scope": "public sandbox execution; simulated GEN only; not a security audit or production-value proof",
              "app_url": "https://demigodd00.github.io/milestonebond/", "repository": "https://github.com/Demigodd00/milestonebond",
              "contract": address, "contract_url": f"https://explorer-studio.genlayer.com/contracts/{address}",
              "source_sha256": DEPLOYMENT["source_sha256"], "source_verified": True, "config": config,
              "project_id": project["id"], "project_status": project["status"], "issue_url": f"https://github.com/{project['repo']}/issues/{project['issue_number']}",
              "issue_sha256": project["issue_sha256"], "sponsor": project["sponsor"], "author": project["author"],
              "remaining_atto": project["remaining"], "stages": stages, "accounting": sponsor, "author_claimable_atto": author["claimable"],
              "transactions": transactions, "outbound_transfers": transfers, "outbound_transfer_verified": len(transfers) == 1,
              "limitations": ["Direct tests are mocked; listed StudioNet transaction receipts are the live execution evidence.",
                              "GitHub repository control, CI runner/dependencies, source availability and criterion quality remain external trust dependencies.",
                              "A review marked ACCEPTED is not a payout until its challenge window closes and finalize_milestone succeeds.",
                              "Withdrawable onchain credits are not proof that an outbound native transfer finalized."]}
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"verified project={project['id']} status={project['status']} stages={[s['status'] for s in stages]} output={OUTPUT}")


if __name__ == "__main__":
    main()
