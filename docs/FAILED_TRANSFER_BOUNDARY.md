# Native transfer failure boundary

MilestoneBond v0.3 is immutable at its deployed StudioNet address. It pays an
EOA using an **external** native GEN transfer. The app must not restore a
withdrawal merely because the child execution reverted: the relevant receipt
field is `value_credited`. If that field is false, restoring the full claim
without replacement funds would make the escrow insolvent. The contract
therefore keeps the claim pending and requires actual balance coverage before
re-crediting it. This preserves accounting integrity, but cannot manufacture
GEN that the protocol did not return.

## Isolated live probes, 13 October 2026

Two separate test-only contracts each accepted 0.001 simulated GEN and sent it
to themselves as a finalized **internal** child. One receiving method was
payable and deliberately reverted; the other was non-payable. Both child
executions finalized with an error, but StudioNet reported
`value_credited=true` and the contract balance remained 0.001 GEN. Thus an
execution error is not evidence of an uncredited transfer.

| Probe | Source | Parent | Child | Child `value_credited` | Balance after |
| --- | --- | --- | --- | --- | --- |
| Payable, reverting receiver | [contract](../contracts/transfer_failure_probe.py) | [parent](https://explorer-studio.genlayer.com/transactions/0x390280a853023d9f31cb4fd688e3802917653d27c6bb7708b208699010c44c24) | [child](https://explorer-studio.genlayer.com/transactions/0x3321cd32dfc932a41acd394f04d900c5882eee560c5974e97fd6ea8a23b5a5a2) | true | 0.001 GEN |
| Non-payable receiver | [contract](../contracts/transfer_failure_probe_v2.py) | [parent](https://explorer-studio.genlayer.com/transactions/0x340c727f9612725142795d0c3d42e9b1274c37e485504703be9a9588993ef0d5) | [child](https://explorer-studio.genlayer.com/transactions/0x8f70cdb2928ca055daf2044300eecb7c8680d6d18e937037b62547a42d10e897) | true | 0.001 GEN |

The [machine-readable v1 record](../deployments/failed_child_probe.json)
and [v2 record](../deployments/failed_child_probe_v2.json) include source hashes,
addresses, transaction hashes and before/after balances. These probes do **not**
exercise MilestoneBond's external EOA transfer or its `value_credited=false`
reconciliation branch. They must not be presented as proof of that branch.

The [GenLayer value-transfer documentation](https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers)
states that failed **internal** messages are not automatically refunded. The
[message documentation](https://docs.genlayer.com/developers/intelligent-contracts/features/messages)
states that Studio does not implement EVM contract interaction beyond value
transfers to EOAs. Consequently we cannot induce an EVM receiver rejection of
MilestoneBond's external transfer on StudioNet. The v0.3 live demonstration
instead proves the successful external child and a wrong-parent rejection; the
uncredited-child path remains covered by adversarial direct-mode receipt tests.

An EOA-only withdrawal restriction could reduce receiver-rejection risk in a
future deployment, but would exclude contract wallets. A prefunded insurance
reserve could cover a *finite* number of losses, but would require additional
capital and cannot guarantee unlimited retries. Neither change is a refund
mechanism. Do not treat v0.3 as production-value insurance or claim that this
protocol-level limitation has been fixed.
