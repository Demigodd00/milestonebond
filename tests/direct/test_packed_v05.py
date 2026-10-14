"""The hash-checked packed release executes the same audited source."""
import ast
import base64
import hashlib
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from build_compact_v05 import DEPLOYABLE as COMPACT
from build_packed_v05 import PACKED, pack


def test_packed_release_is_reproducible_and_hash_bound():
    compact = COMPACT.read_text(encoding="utf-8")
    assert PACKED.read_text(encoding="utf-8") == pack(compact)
    # The exact packed artifact, not just the generator, contains the audited source.
    tree = ast.parse(PACKED.read_text(encoding="utf-8"))
    payload = next(node.value.value for node in tree.body
                   if isinstance(node, ast.Assign) and node.targets[0].id == "_payload")
    decoded = zlib.decompress(base64.b85decode(payload))
    assert decoded == compact.encode("utf-8")
    assert hashlib.sha256(decoded).hexdigest() == hashlib.sha256(compact.encode()).hexdigest()


def test_packed_release_runs_in_genvm_direct_mode(direct_deploy):
    contract = direct_deploy("contracts/milestone_bond_v0_5_packed.py")
    policy = contract.get_config()
    assert policy["version"] == "milestonebond.v0.5"
    assert policy["settlement_proof"] == "GEN_RECEIPT_MESSAGE_AND_EVM_FINALIZATION"
