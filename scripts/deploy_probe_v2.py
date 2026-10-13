"""One-shot deployment of the non-payable receiver StudioNet probe."""
from __future__ import annotations

import json
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.chains import studionet

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / ".local" / "probe-v2-deployment.json"


def main() -> None:
    if JOURNAL.exists():
        raise SystemExit("Probe deployment already journaled; refusing duplicate")
    key = json.loads((ROOT / ".local" / "demo-accounts.json").read_text(encoding="utf-8"))["sponsor"]
    account = Account.from_key(key)
    source = (ROOT / "contracts" / "transfer_failure_probe_v2.py").read_text(encoding="utf-8")
    client = create_client(chain=studionet, account=account)
    tx = str(client.deploy_contract(code=source, account=account, args=[]))
    JOURNAL.write_text(json.dumps({"network": "studionet", "hash": tx}) + "\n", encoding="utf-8")
    print(tx, flush=True)


if __name__ == "__main__":
    main()
