import json

import pytest

from conftest import HEAD1, ID, NOW, addr, iso, mock
from test_milestone_bond import first_accepted


REQUEST = "1" * 64
PARENT = "0x" + "2" * 64
CHILD = "0x" + "3" * 64


def approve(vm, contract, sponsor):
    review = contract.get_project(ID)["milestones"][0]["reviews"][-1]
    vm.sender = sponsor
    contract.approve_submission(ID, review["revision"], review["evidence_hash"])


def test_delivery_needs_exact_sponsor_approval(direct_vm, scenario, direct_charlie):
    contract, sponsor, author = scenario
    direct_vm.sender = author
    contract.accept_project(ID)
    contract.submit_milestone(ID, 11, HEAD1, 101, 1)
    review = contract.get_project(ID)["milestones"][0]["reviews"][-1]
    with direct_vm.expect_revert("Sponsor has not approved"):
        contract.review_milestone(ID, 1)
    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Only sponsor"):
        contract.approve_submission(ID, 1, review["evidence_hash"])
    direct_vm.sender = sponsor
    with direct_vm.expect_revert("exact evidence"):
        contract.approve_submission(ID, 1, "f" * 64)
    contract.approve_submission(ID, 1, review["evidence_hash"])
    with direct_vm.expect_revert("exact evidence"):
        contract.approve_submission(ID, 1, review["evidence_hash"])
    direct_vm.sender = author
    contract.review_milestone(ID, 1)


@pytest.mark.parametrize("suffix,patch,reason", [
    ("/pulls/11", {"state": "closed", "merged_at": "2026-10-12T00:00:00Z"}, "unmerged PR"),
    ("/pulls/11", {"user": {"id": 99, "login": "attacker"}}, "PR is not owned"),
    ("/pulls/11", {"body": "MilestoneBond-Claim: fake"}, "author-wallet claim"),
    ("/commits/" + HEAD1 + "?per_page=100", {"author": {"id": 99}}, "Commit author"),
])
def test_false_author_or_delivery_rejected(direct_vm, scenario, suffix, patch, reason):
    contract, _, author = scenario
    direct_vm.sender = author
    contract.accept_project(ID)
    mock(direct_vm, overrides={suffix: patch}, author_wallet=addr(author))
    with direct_vm.expect_revert(reason):
        contract.submit_milestone(ID, 11, HEAD1, 101, 1)
    assert contract.get_project(ID)["milestones"][0]["revision"] == 0


def test_pr_changed_after_approval_is_rejected(direct_vm, scenario):
    contract, sponsor, author = scenario
    direct_vm.sender = author
    contract.accept_project(ID)
    contract.submit_milestone(ID, 11, HEAD1, 101, 1)
    approve(direct_vm, contract, sponsor)
    direct_vm.sender = author
    mock(direct_vm, overrides={"/pulls/11": {"state": "closed", "merged_at": "2026-10-12T00:00:00Z"}}, author_wallet=addr(author))
    with direct_vm.expect_revert("unmerged PR"):
        contract.review_milestone(ID, 1)


def receipts(vm, contract, author, *, credited=True, child_status="FINALIZED", parent_override=None, child_override=None):
    parent = {"hash": PARENT, "status": "FINALIZED", "from_address": addr(author), "to_address": addr(vm._contract_address),
              "created_timestamp": str(NOW + 600), "tx_data": REQUEST.encode().hex(),
              "messages": [{"messageType": "0", "recipient": addr(author), "value": 10**16, "onAcceptance": False, "data": ""}],
              "triggered_transactions": [CHILD]}
    child = {"hash": CHILD, "status": child_status, "triggered_by": PARENT, "from_address": addr(vm._contract_address),
             "to_address": addr(author), "value": 10**16, "value_credited": credited}
    parent.update(parent_override or {})
    child.update(child_override or {})
    def response(data):
        request = json.loads(data["body"].decode())
        result = parent if request["params"] == [PARENT] else child if request["params"] == [CHILD] else None
        return {"ok": {"response": {"status": 200, "headers": {}, "body": json.dumps({"result": result}).encode()}}}
    vm._live_web_handler = response
    return parent, child


def test_withdrawal_remains_pending_until_reconciled(direct_vm, scenario):
    contract, _, author = first_accepted(direct_vm, scenario)
    direct_vm.sender = author
    contract.withdraw(REQUEST)
    accounting = contract.get_accounting(addr(author))
    assert accounting["claimable"] == "0"
    assert accounting["withdrawn"] == "0"
    assert accounting["pending_out"] == str(10**16)
    with direct_vm.expect_revert("Another transfer awaits"):
        contract.withdraw("4" * 64)
    with direct_vm.expect_revert("Another transfer awaits"):
        contract.withdraw(REQUEST)


def test_confirmed_child_settles_once(direct_vm, scenario):
    contract, _, author = first_accepted(direct_vm, scenario)
    direct_vm.sender = author
    contract.withdraw(REQUEST)
    receipts(direct_vm, contract, author)
    contract.reconcile_withdrawal(PARENT)
    accounting = contract.get_accounting(addr(author))
    assert accounting["pending_out"] == "0"
    assert accounting["claimable"] == "0"
    assert accounting["withdrawn"] == str(10**16)
    with direct_vm.expect_revert("No pending transfer"):
        contract.reconcile_withdrawal(PARENT)
    with direct_vm.expect_revert("Withdrawal request already used"):
        contract.withdraw(REQUEST)


@pytest.mark.parametrize("parent_patch,child_patch,reason", [
    ({"from_address": "0x" + "9" * 40}, {}, "parent mismatch"),
    ({"tx_data": ""}, {}, "request mismatch"),
    ({"messages": []}, {}, "message count mismatch"),
    ({"triggered_transactions": []}, {}, "child unavailable"),
    ({}, {"triggered_by": "0x" + "9" * 64}, "child mismatch"),
    ({}, {"value": 1}, "child mismatch"),
    ({}, {"value_credited": None}, "credit outcome unknown"),
])
def test_false_receipts_never_release_pending(direct_vm, scenario, parent_patch, child_patch, reason):
    contract, _, author = first_accepted(direct_vm, scenario)
    direct_vm.sender = author
    contract.withdraw(REQUEST)
    receipts(direct_vm, contract, author, parent_override=parent_patch, child_override=child_patch)
    with direct_vm.expect_revert(reason):
        contract.reconcile_withdrawal(PARENT)
    accounting = contract.get_accounting(addr(author))
    assert accounting["pending_out"] == str(10**16)
    assert accounting["withdrawn"] == "0"


def test_unfinalized_child_remains_pending(direct_vm, scenario):
    contract, _, author = first_accepted(direct_vm, scenario)
    direct_vm.sender = author
    contract.withdraw(REQUEST)
    receipts(direct_vm, contract, author, child_status="PENDING")
    with direct_vm.expect_revert("child mismatch"):
        contract.reconcile_withdrawal(PARENT)
    assert contract.get_accounting(addr(author))["pending_out"] == str(10**16)


def test_failed_child_requires_real_coverage_before_restoring_credit(direct_vm, scenario):
    contract, sponsor, author = first_accepted(direct_vm, scenario)
    direct_vm.sender = author
    contract.withdraw(REQUEST)
    receipts(direct_vm, contract, author, credited=False)
    with direct_vm.expect_revert("recovery top-up"):
        contract.reconcile_withdrawal(PARENT)
    assert contract.get_accounting(addr(author))["pending_out"] == str(10**16)
    direct_vm.sender = sponsor
    direct_vm.value = 10**16
    contract.top_up_recovery()
    direct_vm.value = 0
    # Direct mode does not emulate contract balances for payable calls or
    # emitted EOA transfers; model the observed post-top-up chain balance.
    direct_vm.deal(direct_vm._contract_address, 3 * 10**16)
    accounting_before = contract.get_accounting(addr(author))
    assert int(accounting_before["contract_balance"]) >= int(accounting_before["locked"]) + int(accounting_before["credited"]) + int(accounting_before["pending_out"]), accounting_before
    contract.reconcile_withdrawal(PARENT)
    accounting = contract.get_accounting(addr(author))
    assert accounting["pending_out"] == "0"
    assert accounting["claimable"] == str(10**16)
    assert accounting["withdrawn"] == "0"
    with direct_vm.expect_revert("No pending transfer"):
        contract.reconcile_withdrawal(PARENT)
    direct_vm.sender = author
    with direct_vm.expect_revert("Withdrawal request already used"):
        contract.withdraw(REQUEST)
