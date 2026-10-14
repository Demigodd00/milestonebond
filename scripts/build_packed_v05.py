"""Build a hash-checked Bradbury deployment wrapper under the 16.7M gas cap.

The wrapper decompresses the AST-identical compact source and checks its SHA
before executing it. The readable source remains the authoritative review
source. Generation is deterministic and direct/integration tests run against
the exact wrapper submitted to the chain.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import zlib
from pathlib import Path

from build_compact_v05 import DEPLOYABLE as COMPACT, READABLE
from build_compact_v05 import compact

ROOT = Path(__file__).resolve().parents[1]
PACKED = ROOT / "contracts" / "milestone_bond_v0_5_packed.py"


def pack(source: str) -> str:
    compressed = zlib.compress(source.encode("utf-8"), level=9)
    encoded = base64.b85encode(compressed).decode("ascii")
    sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    pinned = source.splitlines()[0]
    result = (
        pinned + "\n"
        + "import base64,zlib,hashlib\n"
        + "_payload=" + repr(encoded) + "\n"
        + "_source=zlib.decompress(base64.b85decode(_payload))\n"
        + "if hashlib.sha256(_source).hexdigest()!=" + repr(sha) + ":raise RuntimeError('Packed contract hash mismatch')\n"
        + "exec(compile(_source.decode('utf-8'),'milestone_bond_v0_5_compact.py','exec'))\n"
    )
    ast.parse(result)
    if len(result.encode("utf-8")) >= 18000:
        raise RuntimeError("Packed source did not fit the expected gas envelope")
    return result


def main() -> None:
    readable = READABLE.read_text(encoding="utf-8")
    source = COMPACT.read_text(encoding="utf-8")
    if source != compact(readable):
        raise RuntimeError("Compact source is stale")
    result = pack(source)
    PACKED.write_text(result, encoding="utf-8", newline="\n")
    print({"readable_bytes": len(readable.encode("utf-8")),
           "compact_bytes": len(source.encode("utf-8")),
           "packed_bytes": len(result.encode("utf-8")),
           "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
           "packed_sha256": hashlib.sha256(result.encode("utf-8")).hexdigest()}, flush=True)


if __name__ == "__main__":
    main()
