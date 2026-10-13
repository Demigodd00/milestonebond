<img src="public/milestonebond-logo.png" width="96" alt="MilestoneBond logo">

# MilestoneBond

Ship in public. Pay on proof. MilestoneBond is a standalone GenLayer StudioNet prototype for staged software delivery: a sponsor locks 2–4 fixed tranches, an assigned author submits one PR/commit/CI bundle per stage, the sponsor approves the exact unmerged delivery, and GenLayer validators independently re-fetch the public evidence and agree on every criterion before a tranche is credited. This is **simulated test GEN**, not production escrow or an audit.

[Live app](https://demigodd00.github.io/milestonebond/) · [Steward response and v0.3 evidence](docs/STEWARD_FIXES_V03.md) · [Dedicated source repository](https://github.com/Demigodd00/milestonebond) · [v0.3 StudioNet contract](https://explorer-studio.genlayer.com/contracts/0xa3Cb18a9846a49aF882Cae38fB79923D7F6DcC34) · [Machine-readable live proof](public/verification.json) · [Historical v0.2 run](docs/LIVE_DEMO.md)

The [v0.3 verification record](public/verification.json) reconstructs the completed two-stage project, sponsor approvals, rejected premature review, native child transfer, rejected wrong-parent reconciliation and final accounting from finalized StudioNet receipts. The [historical v0.2 record](public/verification-v0.2.json) is retained separately. An `ACCEPTED` review is still pending until its challenge window closes and the separate finalization transaction succeeds.

## Why it exists

One-off bounties pay for one accepted patch. Real projects ship in stages. MilestoneBond makes those stages explicit and sequential. It does not reuse the PatchBond contract or pay on a PR link alone. The sponsor freezes a GitHub issue body hash, repository and base commit, workflow content and identity, author wallet, allowed source paths, criteria, deadlines and per-stage amounts. Later stages cannot submit until earlier ones settle.

## Reviewer path

1. Open the web app. Its hero diagram and walkthrough are illustrative; **Verify the live run** links the v0.3 receipts, source, negative probes and settlement proof directly from the website.
2. Open **Live projects** and select `MB-LIVE-002` to read the independently deployed v0.3 StudioNet contract. The original frozen base and latest accepted head are shown separately. This view never substitutes simulated data for onchain state.
3. Open **Create project** to generate terms from a public GitHub issue, commit and workflow, then inspect the JSON and exact deposit before signing. The contract re-fetches the sources; browser-generated hashes alone are not authority.
4. Inspect the contract source at `contracts/milestone_bond.py`, the direct tests in `tests/direct`, the [architecture](docs/ARCHITECTURE.md), the [v0.3 deployment record](deployments/studionet_v0.3.json), and the [historical v0.2 record](deployments/studionet.json).
5. For each submitted milestone, compare the project’s onchain criteria and evidence SHA-256 with the pinned GitHub issue, PR head, wallet claim, source and exact CI attempt. Check the separate sponsor approval and validator review. A review is not a payout until its challenge window closes and `finalize_milestone` executes successfully. The [steward response](docs/STEWARD_FIXES_V03.md) collects the direct links.

## Local development

Use Python 3.12, Node 24 and pnpm 11:

```sh
python -m pip install -r requirements-dev.txt
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
- StudioNet is a temporary sandbox. Its GEN has no monetary value, its state can be reset, and smart-contract recipient transfer behavior is not guaranteed. Use test-only externally owned wallets. The [reviewer guide](docs/REVIEW_GUIDE.md) explains wallet funding; v0.3 withdrawals stay pending until the linked child transfer is finalized and reconciled onchain. A failed child requires actual balance coverage before claimable credit is restored; a missing or ambiguous receipt stays pending instead of risking a duplicate payout. A dated verification record remains historical if StudioNet resets.
- There is no background scheduler. Anyone can call the relevant review/finalization or expiry transaction when eligible. A pending review cannot be bypassed by expiry refund.

See [architecture](docs/ARCHITECTURE.md), [deployment guide](docs/DEPLOYMENT.md) and [security notes](docs/SECURITY.md). v0.1 and v0.2 records remain retained; their receipts must not be presented as evidence for the v0.3 protections.
