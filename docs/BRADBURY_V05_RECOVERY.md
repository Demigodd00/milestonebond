# MilestoneBond v0.5 Bradbury recovery evidence

Status: **verified on Bradbury testnet, 14 October 2026**. The
[machine-readable verification record](../public/verification-v0.5.json)
re-reads finalized source, policy, four successful GenLayer executions, the
linked EVM rejection, and restored credit. The historical [v0.4 StudioNet
run](STEWARD_FIXES_V04.md) proves only credited payouts.

## Why this network and release exist

[StudioNet does not implement interactions with EVM contracts beyond EOA
transfers](https://docs.genlayer.com/developers/intelligent-contracts/features/messages).
The steward requested a *finalized external rejection*, not a mocked direct
test or a reverting internal GenLayer child. Bradbury provides an EVM layer,
ghost contracts and external value-transfer execution. The v0.5 source is
separate from immutable v0.4 and keeps its project-specific, sponsor-funded
reserve and one-in-flight payout lock.

The [rejecting receiver deployment](../deployments/bradbury_rejecting_receiver.json)
is a minimal EVM runtime `0x60006000fd`: every call, including one carrying
GEN, reverts. Its [EVM deployment
transaction](https://explorer-bradbury.genlayer.com/tx/0xaf681a59ce5b06d56db25d81da49f94e4e60351c36222cabcc85d959db40cfd8)
was included successfully. A read-only `eth_call` with value returned
`execution reverted`, and the deployed runtime was read back from the chain.
The receiver has no owner or function that can accept or redirect funds.

## Auditable Bradbury release source

Bradbury rejected the 46,376-byte readable contract before broadcast because
its deployment was estimated at 36.9 million gas; the network's per-transaction
ceiling is 16,777,216. Whitespace/comment-only compaction left the Python AST
unchanged but still estimated 29.7 million. The release therefore embeds that
exact compact source in a 13,768-byte, hash-checked compressed wrapper, which
estimated 11.6 million gas. The authoritative review source remains
[`milestone_bond_v0_5.py`](../contracts/milestone_bond_v0_5.py); the exact
submitted wrapper is [`milestone_bond_v0_5_packed.py`](../contracts/milestone_bond_v0_5_packed.py).
[`build_compact_v05.py`](../scripts/build_compact_v05.py) requires AST
equality, and [`build_packed_v05.py`](../scripts/build_packed_v05.py) makes
the wrapper reproducibly and checks SHA-256 before executing. The packed
source is not a separate implementation. Both the wrapper and readable
contract passed GenVM lint, and the direct tests execute both. The deployed
wrapper and policy were read back from finalized state and checked against
the [deployment record](../deployments/bradbury_v0.5.json). Compression makes explorer browsing less convenient, so
reviewers should check the generator, the hashes and the readable source
together rather than treating the packed text alone as an audit.

## Exact reconciliation rule

`withdraw_to` can only spend a project credit held by its caller. It zeroes
that credit, records the caller, requested recipient, value, unique request ID
and exact submitted calldata, then emits one external native transfer at
finalization. A second withdrawal cannot start while this one is pending.

`reconcile_withdrawal` requires both the GenLayer transaction ID and its EVM
finalization hash. Each validator independently reads the finalized GenLayer
receipt, the onchain ConsensusData message array, and the successful EVM
receipt. It checks the exact encoded call, sender, IC address, **one** emitted
external message, recipient and value; then it requires the
`TransactionFinalized(txId)` log in that EVM receipt. A substring match on
the request ID is **not** enough: an unrelated call can contain that string,
so v0.5 compares the full GenLayer calldata encoding byte-for-byte.

The live Bradbury probe established that a reverting EVM receiver currently
emits a message-processor log carrying `handleOp call failed` in the same
finalization receipt, **not** the `ValueWithdrawalFailed` event present in the
SDK's main-contract ABI. The reconciler accepts that exact protocol log from
the observed processor address, linked by transaction ID, plus the
ConsensusMain external-settlement amount log. It also supports an exact
`ValueWithdrawalFailed` event should that event family be used for a pure
value rejection. An absence of either failure signal is not, by itself,
payment proof: the ghost's balance must show the exact single-message debit
before the claim can be marked paid. Incomplete, contradictory or
inaccessible evidence leaves the claim pending.

On a matched failure, the contract measures its actual balance against
locked escrow, other claimable credits, the pending amount and locked reserves.
If value was returned, the claim is restored without consuming reserve. If
there is a shortfall, only this project's remaining sponsor-funded reserve
may cover it. A shortfall exceeding that reserve leaves the claim pending
until test GEN is topped up; no other project's funds are used. An already
reconciled request cannot be replayed, and unused reserve can be released
once to the sponsor only after every project claim settles. This is **finite
testnet coverage**, not an unlimited guarantee of payout.

## Evidence checklist

- [x] Receiver runtime and read-only reject behavior verified on Bradbury.
- [x] A dedicated Bradbury GenLayer probe deployed and its transfer call
  accepted by a validator committee.
- [x] Probe transfer finalized with a linked processor failure log, unchanged
  receiver balance and returned ghost balance. The raw dated record is
  [here](../deployments/bradbury_failure_probe.json), with the GenLayer
  [transaction](https://explorer-bradbury.genlayer.com/tx/0x105289d3c4a107302a8e743e4e6f3138500c27ee0e79664783e6be2f6e3a57e7)
  and [EVM finalization](https://explorer-bradbury.genlayer.com/tx/0xf0c645ea06f965436067ab51626769336f56d0c62464096a686c8190cccf786b).
- [x] v0.5 source linted, direct adversarial tests passed, deployed source
  and policy read back on Bradbury.
- [x] A real MilestoneBond project funded with escrow plus reserve, expired,
  and credited to the sponsor.
- [x] MilestoneBond `withdraw_to` finalized against the rejecting receiver;
  matching message-processor failure log and before/after balances recorded.
- [x] Recovery reconciliation finalized on v0.5 and the restored credit or
  reserve charge read from final state, with no duplicate payout.
- [x] Public app points to the verified v0.5 address and links this dated
  evidence separately from the historical StudioNet v0.4 demo.

## Exact live transaction trail

The sponsor funded project `MB-BRADBURY-FAIL-001` with 0.002 test GEN for
escrow and 0.002 for its separate reserve. All four GenLayer transactions
below have `FINALIZED` status and successful contract execution:

1. [Fund the project](https://explorer-bradbury.genlayer.com/tx/0x9224a9882dd09fde5fb6e53564614d54ae01ea8ea6db06f6d474057039ba717d).
2. [Recover expired escrow](https://explorer-bradbury.genlayer.com/tx/0x4011ed975b3c5693db80ee21bdf051750eba266d2176ad2fde564abccdec1749), creating a 0.002 test-GEN sponsor credit.
3. [Withdraw to the rejecting receiver](https://explorer-bradbury.genlayer.com/tx/0xfe2ebc1e423c1713da68fcd56ee1d73be5a76a01b88ee33782482d3e8457b24b). Its [EVM finalization](https://explorer-bradbury.genlayer.com/tx/0x0f7707a97b218e655ac8a927fe94a832c31b66708db2d0a81d1070087d56e9a8) contains the linked `MessageProcessorFailure` log for one 0.002 test-GEN external message. The receiver stayed at zero and the contract balance stayed at 0.004 test GEN; the claim remained pending, not paid.
4. [Reconcile that exact failed withdrawal](https://explorer-bradbury.genlayer.com/tx/0x746ec103d9996ba283e93bd2bb424e816e9d50380459aee5f2aae12194f2ccd5). Finalized accounting shows `pending_out=0`, no pending withdrawal, `withdrawn=0`, and the full 0.002 test-GEN sponsor credit restored. The 0.002 test-GEN reserve remains locked and unconsumed because the rejected transfer returned its value.

The [verification script](../scripts/verify_live_v05.py) checks the exact
receipt/message/log linkage, before-and-after balances, all four finalized
executions, source hash and final project accounting. This run proves a
restored entitlement after a real failed external transfer. It does **not**
show a second, successful payout or live reserve consumption after an
unreturned loss; those branches remain covered by direct adversarial tests.

## Remaining trust assumptions

Bradbury consensus receipts, EVM logs, the chain RPC and GenLayer's ghost
contract execution are protocol/external dependencies. Validators re-fetch
the public endpoints, but this is not a proof that a malicious or unavailable
RPC can never affect liveness. A successful EVM finalization receipt with no
failure event is treated as a successful external transfer under the protocol
event semantics; any ambiguity must remain pending. This prototype should
not hold production-value escrow or promise recovery beyond its funded
reserve.
