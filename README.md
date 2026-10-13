<img src="public/milestonebond-logo.png" width="96" alt="MilestoneBond logo">

# MilestoneBond

Ship in public. Pay on proof. MilestoneBond is a standalone GenLayer StudioNet prototype for staged software delivery: a sponsor locks 2–4 fixed tranches plus an equal, project-specific recovery reserve. An assigned author submits one PR/commit/CI bundle per stage, the sponsor approves the exact unmerged delivery, and GenLayer validators independently re-fetch the public evidence and agree on every criterion before a tranche is credited. The unused reserve is refundable to the sponsor only after the project's claims settle. This is **simulated test GEN**, not production escrow or an audit.

[Live app](https://demigodd00.github.io/milestonebond/) · [v0.4 StudioNet contract](https://explorer-studio.genlayer.com/contracts/0x9218b57964ae4eBe9c9756bb48b3454a03Ce707D) · [v0.4 reserve proof](public/verification.json) · [Steward response](docs/STEWARD_FIXES_V04.md) · [Reserve design and limits](docs/V04_RESERVE_DESIGN.md) · [v0.3 milestone-payout proof](public/verification-v0.3.json) · [Dedicated source repository](https://github.com/Demigodd00/milestonebond)

The [v0.4 verification record](public/verification.json) reconstructs reserve funding, escrow refund, one-time release of unused reserve and two reconciled native payouts from finalized StudioNet receipts. The [v0.3 record](public/verification-v0.3.json) separately proves the completed two-stage milestone project, sponsor approvals and withdrawal reconciliation on its original contract. Neither a normal credited child nor direct-mode mocks prove a live uncredited external child. An `ACCEPTED` review is still pending until its challenge window closes and separate finalization succeeds.

## Why it exists

One-off bounties pay for one accepted patch. Real projects ship in stages. MilestoneBond makes those stages explicit and sequential. It does not reuse the PatchBond contract or pay on a PR link alone. The sponsor freezes a GitHub issue body hash, repository and base commit, workflow content and identity, author wallet, allowed source paths, criteria, deadlines and per-stage amounts. Later stages cannot submit until earlier ones settle.

## Reviewer path

1. Open the web app. Its hero diagram and walkthrough are illustrative. The v0.4 reserve panel links the current reserve-refund record, while the v0.3 panel preserves the historical two-stage payout evidence.
2. Open **Live projects** and select `MB-RESERVE-001` to read the v0.4 StudioNet contract. The expired fixture demonstrates recovery of escrow and unused reserve, not a completed software milestone. The earlier `MB-LIVE-002` remains on the separate v0.3 contract and its dated record.
3. Open **Create project** to generate terms from a public GitHub issue, commit and workflow, then inspect the JSON and exact deposit before signing. The contract re-fetches the sources; browser-generated hashes alone are not authority.
4. Inspect the [v0.4 contract](contracts/milestone_bond_v0_4.py), [reserve tests](tests/direct/test_reserve_v04.py), [reserve design](docs/V04_RESERVE_DESIGN.md), [v0.4 deployment record](deployments/studionet_v0.4.json), and the original [v0.3 contract](contracts/milestone_bond.py).
5. For the v0.3 milestone run, compare the project's onchain criteria and evidence SHA-256 with the pinned GitHub issue, PR head, wallet claim, source and exact CI attempt. Check sponsor approval and validator review. The [steward response](docs/STEWARD_FIXES_V03.md) collects the direct links.

## Local development

Use Python 3.12, Node 24 and pnpm 11:

```sh
python -m pip install -r requirements-dev.txt
genvm-lint check contracts/milestone_bond_v0_4.py --json
genvm-lint check contracts/milestone_bond.py --json
python scripts/cache_runner.py
pytest tests/direct -q
pnpm install --frozen-lockfile
pnpm test
pnpm build
pnpm dev
```

The direct tests use mocked GitHub and LLM responses. They do not exercise the validator side of GenLayer consensus. The deployment record and any live test report must be read separately; no direct test is labeled live proof.

## Trust boundary and limitations

- The web app prepares and tracks transactions. The contract owns terms, evidence binding, consensus comparison and payout accounting.
- Every validator re-fetches the registered GitHub issue, PR, commit, workflow, exact CI run and job. A changed PR or issue fails closed. Complete source is limited to 24 KB and at most four modified existing files per stage; no arbitrary code runs in the validator prompt.
- The LLM evaluates semantic criteria; it does not set amounts, recipients or final outcomes. The validator compares per-criterion statuses, scope and derived verdict with its independent assessment. Disagreement may stall review rather than produce a payout.
- GitHub API, the repository owner and GitHub Actions are external trust dependencies. A passing CI run does not prove security or that test criteria were adequate. A sponsor must set meaningful observable criteria and a trustworthy workflow. The v0.3 delivery policy is an **open, unmerged PR** owned by the assigned GitHub account, with an exact wallet/head claim, followed by sponsor approval of the captured evidence hash. It is not a merged-code requirement or a proof of human identity. The prototype supports one direct-child commit per milestone, no forks, and no added/deleted/renamed files.
- StudioNet is a temporary sandbox. Its GEN has no monetary value, its state can be reset, and smart-contract recipient transfer behavior is not guaranteed. Use test-only externally owned wallets. The [reviewer guide](docs/REVIEW_GUIDE.md) explains wallet funding. v0.4 charges a confirmed uncredited loss only to its project's funded reserve, up to the remaining reserve balance; further loss needs a donated top-up. Ambiguous receipts stay pending. The live run proves normal credited payouts and reserve refund, **not** a live uncredited child. A dated verification record remains historical if StudioNet resets.
- There is no background scheduler. Anyone can call the relevant review/finalization or expiry transaction when eligible. A pending review cannot be bypassed by expiry refund.

See [architecture](docs/ARCHITECTURE.md), [deployment guide](docs/DEPLOYMENT.md), [reserve design](docs/V04_RESERVE_DESIGN.md) and [security notes](docs/SECURITY.md). Earlier versions remain retained, but their receipts must not be presented as evidence for protections added later.
