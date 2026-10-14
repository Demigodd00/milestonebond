"""Read-only inspection of finalized Bradbury external messages and EVM logs."""
from __future__ import annotations

from web3 import Web3
from genlayer_py import create_client
from genlayer_py.chains import testnet_bradbury


def main() -> None:
    chain = testnet_bradbury
    w3 = Web3(Web3.HTTPProvider(chain.rpc_urls["default"]["http"][0]))
    client = create_client(chain=chain)
    main_address = chain.consensus_main_contract["address"]
    end = w3.eth.block_number
    finalized_topic = w3.keccak(text="TransactionFinalized(bytes32)").hex()
    logs = w3.eth.get_logs({"fromBlock": end - 10000, "toBlock": end,
                            "address": main_address, "topics": [finalized_topic]})
    print(f"finalizations_in_window={len(logs)} latest_block={end}", flush=True)
    found = 0
    for log in reversed(logs[-60:]):
        txid = w3.to_hex(log["topics"][1])
        transaction = client.get_transaction(txid)
        messages = transaction.get("messages") or []
        if not messages:
            continue
        receipt = w3.eth.get_transaction_receipt(log["transactionHash"])
        events = [(entry["address"], entry["topics"][0].hex())
                  for entry in receipt["logs"]]
        print({"txid": txid, "evm_finalization": log["transactionHash"].hex(),
               "execution": transaction.get("tx_execution_result_name"),
               "message_count": len(messages), "messages": str(messages)[:1200],
               "receipt_events": events[:15]}, flush=True)
        found += 1
        if found == 3:
            break
    print(f"found_with_messages={found}", flush=True)


if __name__ == "__main__":
    main()
