"""Read finalized Bradbury IC state despite genlayer-py 0.2.x gen_call drift.

The current node returns an object containing `data` and execution `status`,
while the installed Python SDK expects the `result` itself to be a hex string.
Never silently decode a failed or provisional GenVM execution.
"""
from __future__ import annotations

from genlayer_py.abi import calldata
from genlayer_py.abi.transactions import serialize
from genlayer_py.contracts.utils import make_calldata_object


def read_final(client, address: str, sender: str, method: str, args: list):
    call = serialize([calldata.encode(make_calldata_object(method=method, args=args)), False])
    result = client.provider.make_request("gen_call", [{
        "type": "read", "to": address, "from": sender, "data": call,
        "transaction_hash_variant": "latest-final",
    }]).get("result")
    if not isinstance(result, dict) or not isinstance(result.get("status"), dict):
        raise RuntimeError(f"Malformed Bradbury gen_call response for {method}")
    if result["status"].get("code") != 0 or not isinstance(result.get("data"), str):
        raise RuntimeError(f"Bradbury gen_call failed for {method}: {result.get('status')}")
    return calldata.decode(bytes.fromhex(result["data"]))
