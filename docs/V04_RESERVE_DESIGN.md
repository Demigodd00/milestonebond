# MilestoneBond v0.4: sponsor-funded recovery reserve

This is a new, immutable StudioNet contract. It does not alter the historical
v0.3 address or its payout evidence. It is a simulated-GEN prototype, not
production-value insurance.

## Funding and ownership

For a project with milestone total `X`, the sponsor sends `2X` on creation:
`X` is locked milestone escrow and `X` is a project-specific recovery reserve.
The sponsor does not get an immediate claim against the reserve. A reserve
can cover cumulative *uncredited* native-transfer losses up to `X`; after
that, a further failure remains pending until new funds arrive. Other
projects' escrow and reserves must not be used to fill this project's gap.

Milestone rewards and escrow refunds become **per-project credits**, while
global accounting remains visible. `withdraw(project_id, request_id)` moves
only that project's credit to a single pending native transfer. The request
ID cannot be reused. Anyone may reconcile the exact finalized parent and
linked child, but neither a missing child nor a merely finalized parent is
treated as payment.

For `value_credited=true`, reconciliation records one payout and removes the
corresponding project claim only if the remaining escrow, credits and
reserves are still backed by the contract balance. For
`value_credited=false`, it measures the **actual** balance shortfall; it
never assumes that a failed execution lost or returned GEN. A shortfall no
larger than the transfer amount and the originating project's remaining
reserve is charged to that reserve, then the recipient's claimable credit is
restored. If the reserve is insufficient or receipts are ambiguous, the
claim stays pending, with no second transfer; `top_up_recovery` can fund the
gap. A top-up is a donation, not an investor or sponsor claim.

Once a project is COMPLETE or REFUNDED and **all of its credited/pending
milestone claims have been paid and reconciled**, the sponsor may call
`release_reserve(project_id)` exactly once. This converts the unused amount
to a sponsor credit for that same project. The sponsor then withdraws and
reconciles it through the ordinary native-transfer path. If the reserve
refund transfer itself is uncredited after the reserve has been released,
there is no additional insurance layer; it remains pending until funded.
No finite reserve can guarantee unlimited failures or replace GEN lost by
the underlying protocol.

## Coverage invariant

When no child is in flight, normal withdrawals and reserve release require
`balance >= locked_escrow + claimable_credits + locked_reserves`. A pending
withdrawal is recorded separately because its value is carried in an
asynchronous child; no second withdrawal starts until it is reconciled.
On a finalized uncredited child, the contract includes `pending_out` in its
required-balance calculation before assigning any shortfall to that
project's reserve. New project deposits never count as free recovery funds.

## Evidence limits

The [v0.4 direct tests](../tests/direct/test_reserve_v04.py) cover exact
double funding, per-project segregation, a confirmed lost-value scenario,
a returned-value scenario, tampered receipts, reserve exhaustion, donor
replenishment, and one-time sponsor reserve release. The StudioNet
integration test deploys the actual v0.4 GenVM code and reads its policy.
Live reserve funding, normal child reconciliation, and reserve refund are
recorded separately once finalized. An actual `value_credited=false`
external child has **not** been induced on StudioNet; [Studio's EVM
interaction limitation](https://docs.genlayer.com/developers/intelligent-contracts/features/messages)
still applies. Do not present direct-mode receipt mocks or internal-message
probes as a live test of that external branch.
