# Architecture

## State and payout

`create_project` receives a deposit exactly equal to the sum of 2–4 immutable milestone amounts. It fetches the public GitHub repository, issue, base commit and workflow under GenLayer strict equivalence. The contract stores the issue body and its SHA-256, criteria, paths, fixed recipient, deadlines and funding. A project moves through `AWAITING_AUTHOR → ACTIVE → REVIEW_READY → REVIEW_PENDING`. On acceptance, only the current stage amount is credited to the author, the accepted head becomes the next stage base, and the next stage opens. Final acceptance marks `COMPLETE`. Terminal rejection or eligible expiry credits the sponsor only the **unpaid remainder** and marks `REFUNDED`.

The assigned author alone accepts and submits. Anyone can request review/finalize/recover. Only sponsor or author may challenge once per revision. A challenge re-evaluates the *same* pinned evidence and restarts a 600-second window. Each stage has at most two revisions. A pending review is never eligible for expiry refund. Credits are withdrawn by their owner; accounting tracks deposited = locked + credited + withdrawn, modulo external transfer finality.

## Evidence boundary

Submission binds a PR number, exact head SHA, run ID and attempt. Under strict equivalence, validators independently check:

- canonical public repository ID and unchanged GitHub issue body hash;
- PR head and both PR repositories bound to the registered repository;
- a one-parent, direct-child commit of the prior accepted stage head;
- 1–4 modified existing files, all on the current stage allowlist;
- unchanged pinned workflow bytes and SHA-256;
- successful `push` run on the exact head, pinned workflow ID/path, same repository, within the stage window;
- complete CI job listing, unique required job and all successful steps;
- complete before/after source for changed files, bounded to 24 KB including workflow.

The captured evidence is saved with a canonical SHA-256. Review re-fetches and requires the same digest. A moved PR, edited issue, changed/deleted source or disappearing CI run fails closed. A missing source cannot become acceptance through leader-only metadata.

The prompt treats issue text, code, criteria and challenge as untrusted data. It requests one `SUPPORTED`, `CONTRADICTED` or `INSUFFICIENT` status per criterion, with an exact quote from pinned after-source for support. Schema and quote location are checked. The validator runs its own fetch and assessment, normalizes the leader output, and compares each consequential criterion status, scope flag and derived outcome. It does not merely compare a narrative or accept close numbers. `ACCEPTED` is derived only when scope is okay and **every** criterion is supported. A later deterministic branch, never the LLM, credits the fixed stage amount.

## Frontend boundary

The landing page explains the app and contains a labeled local walkthrough. The live area has no demo fallback. It reads from the verified contract, signs only with the visitor’s wallet, stores a returned hash, polls the exact hash and checks execution success in the finalized receipt. Signing is disabled if the deployment record, chain, onchain config or source hash disagrees. The create page uses an advanced terms JSON editor in v0.1; it validates the deposit sum locally but the contract is authoritative.
