"""Reproduce the gas-bounded Bradbury source from the readable v0.5 source.

Only whitespace and comments are compacted. Names, annotations, statements,
and the full Python AST remain unchanged; the pinned runner header is kept.
"""
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    import python_minifier
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT / ".local" / "tools"))
    import python_minifier

READABLE = ROOT / "contracts" / "milestone_bond_v0_5.py"
DEPLOYABLE = ROOT / "contracts" / "milestone_bond_v0_5_compact.py"


def compact(source: str) -> str:
    pinned = source.splitlines()[0]
    if not pinned.startswith('# { "Depends": "py-genlayer:'):
        raise RuntimeError("Readable contract has no concrete pinned runner")
    body = python_minifier.minify(
        source,
        remove_annotations=False,
        remove_pass=False,
        remove_literal_statements=False,
        combine_imports=False,
        hoist_literals=False,
        rename_locals=False,
        rename_globals=False,
        remove_object_base=False,
        convert_posargs_to_args=False,
        remove_asserts=False,
        remove_debug=False,
        remove_explicit_return_none=False,
        remove_builtin_exception_brackets=False,
        constant_folding=False,
        prefer_single_line=True,
        remove_dead_branches=False,
    )
    result = pinned + "\n" + body + "\n"
    if ast.dump(ast.parse(source), include_attributes=False) != ast.dump(ast.parse(result), include_attributes=False):
        raise RuntimeError("Compact source changed the contract AST")
    return result


def main() -> None:
    source = READABLE.read_text(encoding="utf-8")
    result = compact(source)
    DEPLOYABLE.write_text(result, encoding="utf-8", newline="\n")
    print({"readable_bytes": len(source.encode("utf-8")),
           "deployable_bytes": len(result.encode("utf-8")),
           "deployable_sha256": hashlib.sha256(result.encode("utf-8")).hexdigest(),
           "ast_equal": True}, flush=True)


if __name__ == "__main__":
    main()
