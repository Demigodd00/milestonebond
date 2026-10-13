"""Real GenVM/consensus smoke test before the v0.4 release deployment."""
from gltest import get_contract_factory


def test_v04_deploys_with_reserve_policy():
    factory = get_contract_factory(contract_file_path="milestone_bond_v0_4.py")
    contract = factory.deploy(args=[])
    config = contract.get_config(args=[]).call()
    assert config["version"] == "milestonebond.v0.4"
    assert config["reserve_policy"] == "SPONSOR_FUNDS_100_PERCENT_OF_MILESTONE_BUDGET_REFUND_UNUSED_AFTER_CLAIMS"
