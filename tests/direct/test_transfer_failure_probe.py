"""The probe deliberately schedules, rather than immediately executes, a child."""

import pytest


@pytest.mark.parametrize("source", ["contracts/transfer_failure_probe.py", "contracts/transfer_failure_probe_v2.py"])
def test_probe_requires_value(direct_vm, direct_deploy, direct_alice, source):
    probe = direct_deploy(source)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Probe needs a positive"):
        probe.trigger()
    assert probe.state()["attempted"] == "0"


@pytest.mark.parametrize("source,reason", [
    ("contracts/transfer_failure_probe.py", "Deliberate receiver rejection"),
    ("contracts/transfer_failure_probe_v2.py", "Non-payable receiver must reject"),
])
def test_probe_rejects_a_child(direct_vm, direct_deploy, direct_alice, source, reason):
    probe = direct_deploy(source)
    direct_vm.sender = direct_alice
    direct_vm.value = 10**15
    probe.trigger()
    direct_vm.value = 0
    assert probe.state()["attempted"] == str(10**15)
    with direct_vm.expect_revert(reason):
        probe.reject()
