import json
import pytest
from conftest import NOW, BASE, HEAD1, HEAD2, ID, ISSUE, REPO, addr, iso, mock, terms


def first_accepted(vm, scenario):
    contract, sponsor, author = scenario
    vm.sender = author
    contract.accept_project(ID)
    contract.submit_milestone(ID, 11, HEAD1, 101, 1)
    vm.sender = sponsor
    contract.approve_submission(ID, 1, contract.get_project(ID)["milestones"][0]["reviews"][-1]["evidence_hash"])
    vm.sender = author
    contract.review_milestone(ID, 1)
    vm.warp(iso(NOW + 600))
    contract.finalize_milestone(ID)
    return contract, sponsor, author


def test_two_independent_payouts_and_accounting(direct_vm, scenario):
    contract, sponsor, author = first_accepted(direct_vm, scenario)
    project = contract.get_project(ID)
    assert project["current"] == 1 and project["status"] == "ACTIVE"
    assert project["base_sha"] == HEAD1
    assert project["remaining"] == str(2 * 10**16)
    assert contract.get_accounting(addr(author))["claimable"] == str(10**16)
    mock(direct_vm, base=HEAD1, head=HEAD2, pr=12, run_id=102, after="def create_order(key):\n    if key in orders: return orders[key]\n    if not key: raise ValueError('key required')\n    return new_order(key)\n", run_started=NOW + 600, author_wallet=addr(author))
    contract.submit_milestone(ID, 12, HEAD2, 102, 1)
    direct_vm.sender = sponsor
    contract.approve_submission(ID, 1, contract.get_project(ID)["milestones"][1]["reviews"][-1]["evidence_hash"])
    direct_vm.sender = author
    contract.review_milestone(ID, 1)
    direct_vm.warp(iso(NOW + 1200))
    contract.finalize_milestone(ID)
    assert contract.get_project(ID)["status"] == "COMPLETE"
    assert contract.get_accounting(addr(author))["claimable"] == str(3 * 10**16)
    assert contract.get_accounting(addr(sponsor))["locked"] == "0"
    with direct_vm.expect_revert("Settled or pending"):
        contract.recover_expired(ID)


def test_refund_only_unpaid_remainder(direct_vm, scenario):
    contract, sponsor, author = first_accepted(direct_vm, scenario)
    direct_vm.warp(iso(NOW + 7200))
    contract.recover_expired(ID)
    assert contract.get_project(ID)["status"] == "REFUNDED"
    assert contract.get_accounting(addr(author))["claimable"] == str(10**16)
    assert contract.get_accounting(addr(sponsor))["claimable"] == str(2 * 10**16)


def test_authority_and_exact_deposit(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    mock(direct_vm, author_wallet=addr(direct_bob))
    contract = direct_deploy("contracts/milestone_bond.py")
    direct_vm.sender = direct_alice
    direct_vm.deal(direct_alice, 10**18)
    direct_vm.value = 10**16
    with direct_vm.expect_revert("Deposit must equal"):
        contract.create_project(json.dumps(terms(direct_bob)))
    direct_vm.value = 3 * 10**16
    contract.create_project(json.dumps(terms(direct_bob)))
    direct_vm.value = 0
    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Only assigned author"):
        contract.accept_project(ID)
    with direct_vm.expect_revert("Only assigned author"):
        contract.submit_milestone(ID, 11, HEAD1, 101, 1)


@pytest.mark.parametrize("suffix,patch,reason", [
    ("/pulls/11", {"head": {"sha": "f" * 40, "repo": {"id": 77}}}, "PR head"),
    ("/pulls/11", {"head": {"sha": HEAD1, "repo": {"id": 88}}}, "registered repository"),
    ("/issues/7", {"body": ISSUE + " edited"}, "Frozen issue changed"),
    ("/commits/" + HEAD1 + "?per_page=100", {"parents": [{"sha": "f" * 40}]}, "direct-child"),
    ("/actions/runs/101/attempts/1", {"head_sha": "f" * 40}, "run identity"),
    ("/actions/runs/101/attempts/1", {"workflow_id": 99}, "workflow identity"),
    ("/actions/runs/101/attempts/1", {"conclusion": "failure"}, "push CI must pass"),
    ("/actions/runs/101/attempts/1/jobs?per_page=100", {"total_count": 2}, "Incomplete CI job list"),
])
def test_source_binding_fails_closed(direct_vm, scenario, suffix, patch, reason):
    contract, _, author = scenario
    direct_vm.sender = author
    contract.accept_project(ID)
    mock(direct_vm, overrides={suffix: patch}, author_wallet=addr(author))
    with direct_vm.expect_revert(reason):
        contract.submit_milestone(ID, 11, HEAD1, 101, 1)
    assert contract.get_project(ID)["milestones"][0]["revision"] == 0


def test_negative_review_requires_revision_then_refunds(direct_vm, scenario):
    contract, sponsor, author = scenario
    direct_vm.sender = author
    contract.accept_project(ID)
    mock(direct_vm, status="CONTRADICTED", author_wallet=addr(author))
    contract.submit_milestone(ID, 11, HEAD1, 101, 1)
    direct_vm.sender = sponsor
    contract.approve_submission(ID, 1, contract.get_project(ID)["milestones"][0]["reviews"][-1]["evidence_hash"])
    direct_vm.sender = author
    contract.review_milestone(ID, 1)
    assert contract.get_project(ID)["milestones"][0]["reviews"][0]["outcome"] == "CHANGES_REQUESTED"
    direct_vm.warp(iso(NOW + 600))
    contract.finalize_milestone(ID)
    assert contract.get_project(ID)["status"] == "REVISE"
    direct_vm.warp(iso(NOW + 3600))
    contract.recover_expired(ID)
    assert contract.get_accounting(addr(sponsor))["claimable"] == str(3 * 10**16)


def test_pending_review_cannot_be_refunded(direct_vm, scenario):
    contract, _, author = scenario
    direct_vm.sender = author
    contract.accept_project(ID)
    contract.submit_milestone(ID, 11, HEAD1, 101, 1)
    direct_vm.sender = scenario[1]
    contract.approve_submission(ID, 1, contract.get_project(ID)["milestones"][0]["reviews"][-1]["evidence_hash"])
    direct_vm.sender = author
    contract.review_milestone(ID, 1)
    direct_vm.warp(iso(NOW + 90000))
    with direct_vm.expect_revert("Settled or pending"):
        contract.recover_expired(ID)
    contract.finalize_milestone(ID)
    assert contract.get_project(ID)["current"] == 1


def test_malformed_llm_quote_cannot_accept(direct_vm, scenario):
    contract, _, author = scenario
    direct_vm.sender = author
    contract.accept_project(ID)
    contract.submit_milestone(ID, 11, HEAD1, 101, 1)
    direct_vm.sender = scenario[1]
    contract.approve_submission(ID, 1, contract.get_project(ID)["milestones"][0]["reviews"][-1]["evidence_hash"])
    direct_vm.sender = author
    mock(direct_vm, quote_override="invented source", author_wallet=addr(author))
    with direct_vm.expect_revert("Quote is not in pinned source"):
        contract.review_milestone(ID, 1)
    assert contract.get_project(ID)["status"] == "REVIEW_READY"


def test_changed_public_evidence_cannot_be_reviewed(direct_vm, scenario):
    contract, _, author = scenario
    direct_vm.sender = author
    contract.accept_project(ID)
    contract.submit_milestone(ID, 11, HEAD1, 101, 1)
    direct_vm.sender = scenario[1]
    contract.approve_submission(ID, 1, contract.get_project(ID)["milestones"][0]["reviews"][-1]["evidence_hash"])
    direct_vm.sender = author
    mock(direct_vm, issue=ISSUE + " silently edited", author_wallet=addr(author))
    with direct_vm.expect_revert("Frozen issue changed"):
        contract.review_milestone(ID, 1)
    assert contract.get_project(ID)["status"] == "REVIEW_READY"


def test_insufficient_evidence_does_not_credit_author(direct_vm, scenario):
    contract, _, author = scenario
    direct_vm.sender = author
    contract.accept_project(ID)
    mock(direct_vm, status="INSUFFICIENT", author_wallet=addr(author))
    contract.submit_milestone(ID, 11, HEAD1, 101, 1)
    direct_vm.sender = scenario[1]
    contract.approve_submission(ID, 1, contract.get_project(ID)["milestones"][0]["reviews"][-1]["evidence_hash"])
    direct_vm.sender = author
    contract.review_milestone(ID, 1)
    review = contract.get_project(ID)["milestones"][0]["reviews"][0]
    assert review["outcome"] == "INCONCLUSIVE"
    direct_vm.warp(iso(NOW + 600))
    contract.finalize_milestone(ID)
    assert contract.get_project(ID)["status"] == "REVISE"
    assert contract.get_accounting(addr(author))["claimable"] == "0"
