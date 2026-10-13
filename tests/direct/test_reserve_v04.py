"""Adversarial coverage for the sponsor-funded, refundable v0.4 reserve."""
import json

import pytest

from conftest import ID, NOW, addr, iso, mock, terms
from test_milestone_bond import first_accepted
from test_steward_protections import PARENT, REQUEST, receipts

ESCROW = 3 * 10**16
TRANCHE = 10**16


def mock_receipt(vm, account, request, parent_hash, child_hash, amount, timestamp, credited=True):
    parent = {"hash": parent_hash, "status": "FINALIZED", "from_address": addr(account),
              "to_address": addr(vm._contract_address), "created_timestamp": str(timestamp),
              "tx_data": request.encode().hex(),
              "messages": [{"recipient": addr(account), "value": amount, "onAcceptance": False, "data": ""}],
              "triggered_transactions": [child_hash]}
    child = {"hash": child_hash, "status": "FINALIZED", "triggered_by": parent_hash,
             "from_address": addr(vm._contract_address), "to_address": addr(account),
             "value": amount, "value_credited": credited}

    def response(data):
        wanted = json.loads(data["body"].decode())["params"][0]
        result = parent if wanted == parent_hash else child if wanted == child_hash else None
        return {"ok": {"response": {"status": 200, "headers": {}, "body": json.dumps({"result": result}).encode()}}}

    vm._live_web_handler = response


@pytest.fixture
def reserved(direct_vm, direct_deploy, direct_alice, direct_bob):
    mock(direct_vm, author_wallet=addr(direct_bob))
    contract = direct_deploy("contracts/milestone_bond_v0_4.py")
    direct_vm.sender = direct_alice
    direct_vm.deal(direct_alice, 10**18)
    direct_vm.value = 2 * ESCROW
    contract.create_project(json.dumps(terms(direct_bob)))
    direct_vm.value = 0
    # Direct mode does not automatically model payable contract balances.
    direct_vm.deal(direct_vm._contract_address, 2 * ESCROW)
    return contract, direct_alice, direct_bob


def test_exact_double_funding_is_required(direct_vm, direct_deploy, direct_alice, direct_bob):
    mock(direct_vm, author_wallet=addr(direct_bob))
    contract = direct_deploy("contracts/milestone_bond_v0_4.py")
    direct_vm.sender = direct_alice
    direct_vm.value = ESCROW
    with direct_vm.expect_revert("milestones plus equal recovery reserve"):
        contract.create_project(json.dumps(terms(direct_bob)))
    direct_vm.value = 0
    assert contract.get_accounting(addr(direct_alice))["reserve_locked"] == "0"


def test_registration_separates_escrow_and_refundable_reserve(reserved):
    contract, sponsor, _ = reserved
    account = contract.get_accounting(addr(sponsor))
    project = contract.get_project(ID)
    assert account["deposited"] == str(2 * ESCROW)
    assert account["locked"] == str(ESCROW)
    assert account["reserve_locked"] == str(ESCROW)
    assert project["reserve_remaining"] == str(ESCROW)
    assert project["claims_outstanding"] == "0"
    assert contract.get_config()["version"] == "milestonebond.v0.4"


def test_failed_child_consumes_only_its_project_reserve(direct_vm, reserved):
    contract, sponsor, author = first_accepted(direct_vm, reserved)
    direct_vm.sender = author
    contract.withdraw(ID, REQUEST)
    direct_vm.deal(direct_vm._contract_address, 2 * ESCROW - TRANCHE)
    receipts(direct_vm, contract, author, credited=False)
    contract.reconcile_withdrawal(PARENT)
    accounting = contract.get_accounting(addr(author))
    project = contract.get_project(ID)
    assert accounting["pending_out"] == "0"
    assert accounting["claimable"] == str(TRANCHE)
    assert accounting["reserve_locked"] == str(ESCROW - TRANCHE)
    assert accounting["reserve_consumed"] == str(TRANCHE)
    assert project["reserve_remaining"] == str(ESCROW - TRANCHE)
    assert project["claims_outstanding"] == str(TRANCHE)
    assert contract.get_project_accounting(ID, addr(author))["claimable"] == str(TRANCHE)
    direct_vm.sender = sponsor
    with direct_vm.expect_revert("Project escrow not settled"):
        contract.release_reserve(ID)


def test_refunded_value_does_not_spend_reserve(direct_vm, reserved):
    contract, _, author = first_accepted(direct_vm, reserved)
    direct_vm.sender = author
    contract.withdraw(ID, REQUEST)
    # Failed child but balance actually returned: no loss may be charged.
    receipts(direct_vm, contract, author, credited=False)
    contract.reconcile_withdrawal(PARENT)
    assert contract.get_project(ID)["reserve_remaining"] == str(ESCROW)
    assert contract.get_accounting(addr(author))["claimable"] == str(TRANCHE)


def test_confirmed_payout_preserves_reserve_and_releases_it_once(direct_vm, reserved):
    contract, sponsor, author = first_accepted(direct_vm, reserved)
    direct_vm.warp(iso(NOW + 7200))
    direct_vm.sender = sponsor
    contract.recover_expired(ID)
    assert contract.get_project(ID)["status"] == "REFUNDED"
    with direct_vm.expect_revert("Project claims remain"):
        contract.release_reserve(ID)
    # The author has 0.01 and sponsor has 0.02; both must clear first.
    direct_vm.sender = author
    contract.withdraw(ID, REQUEST)
    direct_vm.deal(direct_vm._contract_address, 2 * ESCROW - TRANCHE)
    mock_receipt(direct_vm, author, REQUEST, PARENT, "0x" + "3" * 64, TRANCHE, NOW + 7200)
    contract.reconcile_withdrawal(PARENT)
    direct_vm.sender = sponsor
    request2 = "4" * 64
    parent2 = "0x" + "5" * 64
    contract.withdraw(ID, request2)
    direct_vm.deal(direct_vm._contract_address, ESCROW)
    mock_receipt(direct_vm, sponsor, request2, parent2, "0x" + "6" * 64, 2 * TRANCHE, NOW + 7200)
    contract.reconcile_withdrawal(parent2)
    assert contract.get_project(ID)["claims_outstanding"] == "0"
    contract.release_reserve(ID)
    project = contract.get_project(ID)
    assert project["reserve_released"] is True
    assert project["reserve_remaining"] == "0"
    assert contract.get_project_accounting(ID, addr(sponsor))["claimable"] == str(ESCROW)
    assert contract.get_accounting(addr(sponsor))["reserve_locked"] == "0"
    with direct_vm.expect_revert("reserve already released"):
        contract.release_reserve(ID)


def test_unknown_child_cannot_spend_reserve(direct_vm, reserved):
    contract, _, author = first_accepted(direct_vm, reserved)
    direct_vm.sender = author
    contract.withdraw(ID, REQUEST)
    direct_vm.deal(direct_vm._contract_address, 2 * ESCROW - TRANCHE)
    receipts(direct_vm, contract, author, credited=False, child_override={"triggered_by": "0x" + "9" * 64})
    with direct_vm.expect_revert("child mismatch"):
        contract.reconcile_withdrawal(PARENT)
    assert contract.get_accounting(addr(author))["pending_out"] == str(TRANCHE)
    assert contract.get_project(ID)["reserve_remaining"] == str(ESCROW)


def test_credited_child_does_not_hide_other_claims_deficit(direct_vm, reserved):
    contract, _, author = first_accepted(direct_vm, reserved)
    direct_vm.sender = author
    contract.withdraw(ID, REQUEST)
    direct_vm.deal(direct_vm._contract_address, 2 * ESCROW - TRANCHE - 1)
    receipts(direct_vm, contract, author, credited=True)
    with direct_vm.expect_revert("Other claims lost backing"):
        contract.reconcile_withdrawal(PARENT)
    assert contract.get_accounting(addr(author))["pending_out"] == str(TRANCHE)
    assert contract.get_project(ID)["claims_outstanding"] == str(TRANCHE)


def test_reserve_exhaustion_cannot_spend_another_projects_funds(direct_vm, reserved):
    contract, sponsor, author = reserved
    other = terms(author)
    other["id"] = "MB-OTHER-002"
    direct_vm.sender = sponsor
    direct_vm.value = 2 * ESCROW
    contract.create_project(json.dumps(other))
    direct_vm.value = 0
    direct_vm.deal(direct_vm._contract_address, 4 * ESCROW)
    contract, _, author = first_accepted(direct_vm, reserved)
    direct_vm.sender = author
    with direct_vm.expect_revert("No claimable credit"):
        contract.withdraw(other["id"], "f" * 64)
    balance = 4 * ESCROW
    for i in range(3):
        direct_vm.sender = author
        request = format(i + 1, "x") * 64
        parent = "0x" + format(i + 4, "x") * 64
        child = "0x" + format(i + 7, "x") * 64
        contract.withdraw(ID, request)
        balance -= TRANCHE
        direct_vm.deal(direct_vm._contract_address, balance)
        mock_receipt(direct_vm, author, request, parent, child, TRANCHE, NOW + 600, credited=False)
        contract.reconcile_withdrawal(parent)
        assert contract.get_accounting(addr(author))["claimable"] == str(TRANCHE)
    assert contract.get_project(ID)["reserve_remaining"] == "0"
    assert contract.get_project(other["id"])["reserve_remaining"] == str(ESCROW)
    request = "a" * 64
    parent = "0x" + "b" * 64
    child = "0x" + "c" * 64
    contract.withdraw(ID, request)
    balance -= TRANCHE
    direct_vm.deal(direct_vm._contract_address, balance)
    mock_receipt(direct_vm, author, request, parent, child, TRANCHE, NOW + 600, credited=False)
    with direct_vm.expect_revert("exceeds funded reserve"):
        contract.reconcile_withdrawal(parent)
    assert contract.get_accounting(addr(author))["pending_out"] == str(TRANCHE)
    assert contract.get_project(other["id"])["reserve_remaining"] == str(ESCROW)
    direct_vm.sender = sponsor
    direct_vm.value = TRANCHE
    contract.top_up_recovery()
    direct_vm.value = 0
    direct_vm.deal(direct_vm._contract_address, balance + TRANCHE)
    contract.reconcile_withdrawal(parent)
    assert contract.get_accounting(addr(author))["pending_out"] == "0"
    assert contract.get_accounting(addr(author))["claimable"] == str(TRANCHE)
    assert contract.get_project(other["id"])["reserve_remaining"] == str(ESCROW)
    direct_vm.sender = author
    with direct_vm.expect_revert("already used"):
        contract.withdraw(ID, request)
