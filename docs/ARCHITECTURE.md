# Architecture

## Current v0.5 reserve and settlement

Bradbury v0.5 receives exactly twice the 2–4 fixed milestone amounts: one
share funds escrow, and an equal project-specific reserve covers only
confirmed unreturned withdrawal loss. Unused reserve can be released to its
sponsor once all project claims settle. A withdrawal creates one pending
external transfer. Reconciliation independently binds its exact finalized
GenLayer call and message to the EVM finalization receipt, failure/settlement
log and real balances. A confirmed rejected transfer restored a claim in the
[live v0.5 evidence](BRADBURY_V05_RECOVERY.md); it did not consume reserve or
pay the recipient. Incomplete evidence stays pending. The older StudioNet
child-receipt path below is historical, not v0.5's settlement mechanism.

## Historical v0.3 state and payout

`create_project` receives a deposit exactly equal to the sum of 2–4 immutable milestone amounts. It fetches the public GitHub repository, issue, base commit and workflow under GenLayer strict equivalence. The contract stores the issue body and its SHA-256, criteria, paths, fixed recipient, deadlines and funding. A project moves through `AWAITING_AUTHOR → ACTIVE → REVIEW_READY → REVIEW_PENDING`. On acceptance, only the current stage amount is credited to the author, the accepted head becomes the next stage base, and the next stage opens. Final acceptance marks `COMPLETE`. Terminal rejection or eligible expiry credits the sponsor only the **unpaid remainder** and marks `REFUNDED`.

The assigned author wallet alone accepts and submits. The distinct sponsor wallet must approve the submitted evidence hash before anyone can request review. Anyone can then request review/finalize/recover. Only sponsor or author may challenge once per revision. A challenge re-evaluates the *same* pinned evidence and restarts a 600-second window. Each stage has at most two revisions. A pending review is never eligible for expiry refund.

The explicit delivery policy is `SPONSOR_APPROVED_UNMERGED_COMMIT`: the PR must remain open and unmerged at submission and review; an accepted stage does **not** assert that code merged. Registration freezes the assigned GitHub login and numeric user ID. Submission requires the PR owner and GitHub-associated commit author to match that ID, an exact PR-body `MilestoneBond-Claim: <project> <wallet> <head SHA>` line, and a call signed by the assigned wallet. Sponsor approval then binds the captured evidence hash. This is not a cryptographic proof of a human identity or of a GitHub account controlled by the wallet; it is a jointly authenticated workflow with explicit external GitHub trust.

Withdrawal is two-phase. `withdraw(request_id)` moves the caller's credit to one global `pending_out` slot and emits one finalized native transfer. `reconcile_withdrawal(parent_hash)` has validators fetch the StudioNet parent and its exact triggered child, checking the unique request ID in calldata, timestamp, sender, contract, recipient, amount, linkage, finality, and `value_credited`. A confirmed credit closes pending and increments `withdrawn` once. An unknown or inconsistent receipt leaves the entitlement pending and blocks another transfer. A finalized failed child can restore claimable credit only when the real contract balance covers all locked, claimable and pending obligations; `top_up_recovery` can provide replacement simulated GEN if the protocol did not refund the failed transfer. The donor does not gain a claim. Direct-mode tests model the receipts and cannot prove StudioNet's external-transfer behavior.

## Evidence boundary

Submission binds a PR number, exact head SHA, run ID and attempt. Under strict equivalence, validators independently check:

- canonical public repository ID and unchanged GitHub issue body hash;
- PR head and both PR repositories bound to the registered repository, still open and unmerged;
- frozen GitHub user ID matching the PR owner and commit author, plus the exact wallet claim in the PR body;
- a one-parent, direct-child commit of the prior accepted stage head;
- 1–4 modified existing files, all on the current stage allowlist;
- unchanged pinned workflow bytes and SHA-256;
- successful `push` run on the exact head, pinned workflow ID/path, same repository, within the stage window;
- complete CI job listing, unique required job and all successful steps;
- complete before/after source for changed files, bounded to 24 KB including workflow.

The captured evidence is saved with a canonical SHA-256. Review re-fetches and requires the same digest. A moved PR, edited issue, changed/deleted source or disappearing CI run fails closed. A missing source cannot become acceptance through leader-only metadata.

The prompt treats issue text, code, criteria and challenge as untrusted data. It requests one `SUPPORTED`, `CONTRADICTED` or `INSUFFICIENT` status per criterion, with an exact quote from pinned after-source for support. Schema and quote location are checked. The validator runs its own fetch and assessment, normalizes the leader output, and compares each consequential criterion status, scope flag and derived outcome. It does not merely compare a narrative or accept close numbers. `ACCEPTED` is derived only when scope is okay and **every** criterion is supported. A later deterministic branch, never the LLM, credits the fixed stage amount.

## Frontend boundary

The landing page explains the app and contains a labeled local walkthrough. The live area has no demo fallback. It reads from the verified contract, signs only with the visitor’s wallet, stores a returned hash, polls the exact hash and checks execution success in the finalized receipt. Signing is disabled if the deployment record, chain, onchain config or source hash disagrees. The create page has a guided builder that fetches public GitHub issue, commit, workflow content and workflow ID, calculates SHA-256 commitments, and fills a reviewable JSON editor. Browser preparation is not authoritative: the contract re-fetches these sources and validates the exact deposit.
