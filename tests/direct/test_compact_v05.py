"""The submitted compact source is reproducible and executable, not a fork."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from build_compact_v05 import READABLE, DEPLOYABLE, compact


def test_compact_source_matches_readable_ast_exactly():
    assert DEPLOYABLE.read_text(encoding="utf-8") == compact(READABLE.read_text(encoding="utf-8"))


def test_compact_release_runs_in_genvm_direct_mode(direct_deploy):
    contract = direct_deploy("contracts/milestone_bond_v0_5_compact.py")
    policy = contract.get_config()
    assert policy["version"] == "milestonebond.v0.5"
    assert policy["settlement_proof"] == "GEN_RECEIPT_MESSAGE_AND_EVM_FINALIZATION"
