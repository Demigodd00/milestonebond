"""Receipt-forgery and project-reserve tests for the Bradbury settlement path."""
import json

import pytest
from genlayer_py.abi import calldata
from genlayer_py.abi.transactions import serialize
from genlayer_py.contracts.utils import make_calldata_object

from conftest import ID, addr, mock, terms
from test_milestone_bond import first_accepted

PARENT = "0x" + "2" * 64
FINAL = "0x" + "3" * 64
REQUEST = "1" * 64
ESCROW = 3 * 10**16
TRANCHE = 10**16
CONSENSUS = "0x0112bf6e83497965a5fdd6dad1e447a6e004271d"
FINALIZED_TOPIC = "0x24196ec40f90671b7144e716978686b4f3c7d6b00b23da3971ef2b52af27d87f"
FAILED_TOPIC = "0xd7d0ee861c0ebf42599b922e8f4ad0cafed951841610157bcd56110f49ced8ee"
PROCESSOR = "0x27872802226532fcd7fea2f00addbffbd3380ade"
PROCESSOR_FAILURE_TOPIC = "0x5ae8e754fbc8b7b56c89e264bdcd8bb847036b23ac1a0f791f48b62438f2bab9"
EXTERNAL_SETTLEMENT_TOPIC = "0x6565c26927b368d6e75314c8bf1c1e2847f1cdd47b89e10ae002a2889da4d150"


@pytest.fixture
def ready(direct_vm, direct_deploy, direct_alice, direct_bob):
    mock(direct_vm, author_wallet=addr(direct_bob))
    contract = direct_deploy("contracts/milestone_bond_v0_5.py")
    direct_vm.sender = direct_alice
    direct_vm.deal(direct_alice, 10**18)
    direct_vm.value = 2 * ESCROW
    contract.create_project(json.dumps(terms(direct_bob)))
    direct_vm.value = 0
    direct_vm.deal(direct_vm._contract_address, 2 * ESCROW)
    return first_accepted(direct_vm, (contract, direct_alice, direct_bob))


def encoded(method, args):
    return serialize([calldata.encode(make_calldata_object(method=method, args=args)), False])[2:]


def transaction_data(recipient, *, amount=TRANCHE, message_type=0, status=7):
    # ABI return of ConsensusData.getTransactionData: tuple head plus one
    # SubmittedMessage element. Only fields the contract reads are populated.
    word = lambda value: int(value).to_bytes(32, "big")
    head = [0] * 25
    head[12] = 25 * 32
    head[17] = status
    head[18] = int(PARENT, 16)
    recipient_hex = addr(recipient) if isinstance(recipient, bytes) else str(recipient)
    message = [1, 32, message_type, int(recipient_hex, 16), amount, 192, 0, 0, 0]
    return "0x" + (word(32) + b"".join(word(value) for value in head + message)).hex()


def receipts(vm, account, recipient, *, failed, method="withdraw_to", duplicate_failed=False, parent_patch=None,
             receipt_patch=None, failed_patch=None, protocol_failure=False, message_patch=None,
             processor_patch=None, settlement_patch=None, duplicate_processor=False):
    arguments = [ID, REQUEST] + ([str(recipient)] if method == "withdraw_to" else [])
    parent = {"id": PARENT, "status": 7, "txExecutionResult": 1,
              "sender": addr(account), "recipient": addr(vm._contract_address),
              "txCallData": encoded(method, arguments)}
    final_event = {"address": CONSENSUS, "topics": [FINALIZED_TOPIC, PARENT], "data": "0x"}
    failed_event = {"address": CONSENSUS,
                    "topics": [FAILED_TOPIC, PARENT,
                               "0x" + str(recipient)[2:].lower().rjust(64, "0")],
                    "data": hex(TRANCHE)}
    failed_event.update(failed_patch or {})
    reason = b"handleOp call failed"
    processor_event = {"address": PROCESSOR,
                       "topics": [PROCESSOR_FAILURE_TOPIC, PARENT, "0x" + "7" * 64],
                       "data": "0x" + (32).to_bytes(32, "big").hex()
                       + len(reason).to_bytes(32, "big").hex() + reason.ljust(32, b"\0").hex()}
    processor_event.update(processor_patch or {})
    settlement_event = {"address": CONSENSUS, "topics": [EXTERNAL_SETTLEMENT_TOPIC, PARENT],
                        "data": "0x" + TRANCHE.to_bytes(32, "big").hex() + (1).to_bytes(32, "big").hex()}
    settlement_event.update(settlement_patch or {})
    receipt = {"transactionHash": FINAL, "to": CONSENSUS, "status": "0x1",
               "logs": [final_event]
               + ([failed_event] * (2 if duplicate_failed else 1) if failed else [])
               + ([processor_event] * (2 if duplicate_processor else 1) + [settlement_event]
                  if protocol_failure else [])}
    parent.update(parent_patch or {})
    receipt.update(receipt_patch or {})

    def response(data):
        payload = json.loads(data["body"].decode())
        result = (parent if payload["method"] == "gen_getTransactionReceipt"
                  else transaction_data(recipient, **(message_patch or {})) if payload["method"] == "eth_call"
                  else receipt)
        return {"ok": {"response": {"status": 200, "headers": {},
                                    "body": json.dumps({"jsonrpc": "2.0", "id": 1,
                                                        "result": result}).encode()}}}

    vm._live_web_handler = response


def test_rejecting_recipient_restores_credit_with_returned_value(direct_vm, ready, direct_charlie):
    contract, sponsor, author = ready
    assert contract.get_config()["settlement_proof"] == "GEN_RECEIPT_MESSAGE_AND_EVM_FINALIZATION"
    direct_vm.sender = author
    contract.withdraw_to(ID, REQUEST, str(direct_charlie))
    assert contract.get_accounting(addr(author))["pending_out"] == str(TRANCHE)
    receipts(direct_vm, author, direct_charlie, failed=True)
    contract.reconcile_withdrawal(PARENT, FINAL)
    state = contract.get_accounting(addr(author))
    assert state["claimable"] == str(TRANCHE)
    assert state["pending_out"] == "0"
    assert state["withdrawn"] == "0"
    assert state["reserve_consumed"] == "0"
    with direct_vm.expect_revert("No pending transfer"):
        contract.reconcile_withdrawal(PARENT, FINAL)
    with direct_vm.expect_revert("Withdrawal request already used"):
        contract.withdraw_to(ID, REQUEST, str(direct_charlie))


def test_failed_transfer_shortfall_consumes_only_funded_reserve(direct_vm, ready, direct_charlie):
    contract, _, author = ready
    direct_vm.sender = author
    contract.withdraw_to(ID, REQUEST, str(direct_charlie))
    direct_vm.deal(direct_vm._contract_address, 2 * ESCROW - TRANCHE)
    receipts(direct_vm, author, direct_charlie, failed=True)
    contract.reconcile_withdrawal(PARENT, FINAL)
    assert contract.get_accounting(addr(author))["reserve_consumed"] == str(TRANCHE)
    assert contract.get_project(ID)["reserve_remaining"] == str(ESCROW - TRANCHE)
    assert contract.get_project_accounting(ID, addr(author))["claimable"] == str(TRANCHE)


def test_live_bradbury_processor_failure_restores_credit(direct_vm, ready, direct_charlie):
    contract, _, author = ready
    direct_vm.sender = author
    contract.withdraw_to(ID, REQUEST, str(direct_charlie))
    receipts(direct_vm, author, direct_charlie, failed=False, protocol_failure=True)
    contract.reconcile_withdrawal(PARENT, FINAL)
    state = contract.get_accounting(addr(author))
    assert state["claimable"] == str(TRANCHE)
    assert state["pending_out"] == "0"
    assert state["withdrawn"] == "0"
    assert state["reserve_consumed"] == "0"


def test_live_bradbury_processor_failure_shortfall_uses_reserve(direct_vm, ready, direct_charlie):
    contract, _, author = ready
    direct_vm.sender = author
    contract.withdraw_to(ID, REQUEST, str(direct_charlie))
    direct_vm.deal(direct_vm._contract_address, 2 * ESCROW - TRANCHE)
    receipts(direct_vm, author, direct_charlie, failed=False, protocol_failure=True)
    contract.reconcile_withdrawal(PARENT, FINAL)
    assert contract.get_accounting(addr(author))["reserve_consumed"] == str(TRANCHE)
    assert contract.get_project_accounting(ID, addr(author))["claimable"] == str(TRANCHE)


@pytest.mark.parametrize("message_patch,reason", [
    ({"amount": TRANCHE + 1}, "message mismatch"),
    ({"message_type": 1}, "message mismatch"),
    ({"status": 5}, "transaction data mismatch"),
])
def test_other_message_cannot_impersonate_withdrawal(direct_vm, ready, direct_charlie, message_patch, reason):
    contract, _, author = ready
    direct_vm.sender = author
    contract.withdraw_to(ID, REQUEST, str(direct_charlie))
    receipts(direct_vm, author, direct_charlie, failed=False, protocol_failure=True,
             message_patch=message_patch)
    with direct_vm.expect_revert(reason):
        contract.reconcile_withdrawal(PARENT, FINAL)
    assert contract.get_accounting(addr(author))["pending_out"] == str(TRANCHE)


@pytest.mark.parametrize("processor_patch,settlement_patch,duplicate_processor,reason", [
    ({"address": "0x" + "9" * 40}, None, False, "External processor failure mismatch"),
    ({"data": "0x"}, None, False, "External processor failure mismatch"),
    (None, {"data": "0x" + "0" * 128}, False, "External settlement value mismatch"),
    (None, None, True, "Ambiguous failed withdrawal events"),
])
def test_processor_evidence_tampering_does_not_restore_credit(
        direct_vm, ready, direct_charlie, processor_patch, settlement_patch, duplicate_processor, reason):
    contract, _, author = ready
    direct_vm.sender = author
    contract.withdraw_to(ID, REQUEST, str(direct_charlie))
    receipts(direct_vm, author, direct_charlie, failed=False, protocol_failure=True,
             processor_patch=processor_patch, settlement_patch=settlement_patch,
             duplicate_processor=duplicate_processor)
    if processor_patch and "address" in processor_patch:
        # An unrelated address cannot provide a recognized failure event;
        # it must not be treated as a refund. This is a success outcome when
        # no trusted failure event exists, so use a balance shortfall.
        direct_vm.deal(direct_vm._contract_address, 2 * ESCROW - TRANCHE)
        contract.reconcile_withdrawal(PARENT, FINAL)
        assert contract.get_accounting(addr(author))["claimable"] == "0"
    else:
        with direct_vm.expect_revert(reason):
            contract.reconcile_withdrawal(PARENT, FINAL)
        assert contract.get_accounting(addr(author))["pending_out"] == str(TRANCHE)


@pytest.mark.parametrize("parent_patch,receipt_patch,failed_patch,reason", [
    ({"sender": "0x" + "9" * 40}, None, None, "parent mismatch"),
    ({"status": 5}, None, None, "parent mismatch"),
    ({"txExecutionResult": 2}, None, None, "parent mismatch"),
    ({"txCallData": ""}, None, None, "call identity mismatch"),
    (None, {"status": "0x0"}, None, "EVM receipt mismatch"),
    (None, {"transactionHash": "0x" + "8" * 64}, None, "EVM receipt mismatch"),
    (None, {"logs": []}, None, "finalization event missing"),
    (None, None, {"data": hex(TRANCHE + 1)}, "does not match recipient and amount"),
    (None, None, {"topics": [FAILED_TOPIC, PARENT, "0x" + "9" * 64]}, "does not match recipient and amount"),
])
def test_forged_or_incomplete_chain_evidence_cannot_release_claim(
        direct_vm, ready, direct_charlie, parent_patch, receipt_patch, failed_patch, reason):
    contract, _, author = ready
    direct_vm.sender = author
    contract.withdraw_to(ID, REQUEST, str(direct_charlie))
    receipts(direct_vm, author, direct_charlie, failed=True,
             parent_patch=parent_patch, receipt_patch=receipt_patch,
             failed_patch=failed_patch)
    with direct_vm.expect_revert(reason):
        contract.reconcile_withdrawal(PARENT, FINAL)
    accounting = contract.get_accounting(addr(author))
    assert accounting["pending_out"] == str(TRANCHE)
    assert accounting["withdrawn"] == "0"


def test_duplicate_failure_events_cannot_reconcile(direct_vm, ready, direct_charlie):
    contract, _, author = ready
    direct_vm.sender = author
    contract.withdraw_to(ID, REQUEST, str(direct_charlie))
    receipts(direct_vm, author, direct_charlie, failed=True, duplicate_failed=True)
    with direct_vm.expect_revert("Ambiguous failed withdrawal events"):
        contract.reconcile_withdrawal(PARENT, FINAL)
    assert contract.get_accounting(addr(author))["pending_out"] == str(TRANCHE)


def test_finalized_success_pays_once(direct_vm, ready):
    contract, _, author = ready
    direct_vm.sender = author
    contract.withdraw(ID, REQUEST)
    direct_vm.deal(direct_vm._contract_address, 2 * ESCROW - TRANCHE)
    receipts(direct_vm, author, author, failed=False, method="withdraw")
    contract.reconcile_withdrawal(PARENT, FINAL)
    accounting = contract.get_accounting(addr(author))
    assert accounting["pending_out"] == "0"
    assert accounting["claimable"] == "0"
    assert accounting["withdrawn"] == str(TRANCHE)


def test_no_failure_log_without_balance_debit_stays_pending(direct_vm, ready):
    contract, _, author = ready
    direct_vm.sender = author
    contract.withdraw(ID, REQUEST)
    receipts(direct_vm, author, author, failed=False, method="withdraw")
    with direct_vm.expect_revert("Successful transfer lacks exact balance debit"):
        contract.reconcile_withdrawal(PARENT, FINAL)
    assert contract.get_accounting(addr(author))["pending_out"] == str(TRANCHE)


def test_unrelated_finalized_call_cannot_impersonate_withdrawal(direct_vm, ready, direct_charlie):
    contract, _, author = ready
    direct_vm.sender = author
    contract.withdraw_to(ID, REQUEST, str(direct_charlie))
    decoy = encoded("create_project", ["withdraw_to " + ID + " " + REQUEST + " " + str(direct_charlie)])
    receipts(direct_vm, author, direct_charlie, failed=False,
             parent_patch={"txCallData": decoy})
    with direct_vm.expect_revert("Withdrawal call identity mismatch"):
        contract.reconcile_withdrawal(PARENT, FINAL)
    assert contract.get_accounting(addr(author))["pending_out"] == str(TRANCHE)
