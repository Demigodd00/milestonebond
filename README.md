<img src="public/milestonebond-logo.png" width="96" alt="MilestoneBond logo">

# MilestoneBond

Ship in public. Pay on proof. MilestoneBond is a standalone GenLayer Bradbury testnet prototype for staged software delivery: a sponsor locks 2–4 fixed tranches plus an equal, project-specific recovery reserve. An assigned author submits one PR/commit/CI bundle per stage, the sponsor approves the exact unmerged delivery, and GenLayer validators independently re-fetch the public evidence and agree on every criterion before a tranche is credited. The unused reserve is refundable to the sponsor only after the project's claims settle. This is **test GEN**, not production escrow or an audit.

[Live app](https://demigodd00.github.io/milestonebond/) · [v0.5 Bradbury contract](https://explorer-bradbury.genlayer.com/address/0xf7358a08822cbc439a83225b8cf48f21b10468dc) · [finalized failure-and-recovery proof](public/verification-v0.5.json) · [reviewer evidence trail](docs/BRADBURY_V05_RECOVERY.md) · [historical v0.4 StudioNet reserve proof](public/verification.json) · [v0.3 milestone-payout proof](public/verification-v0.3.json) · [Dedicated source repository](https://github.com/Demigodd00/milestonebond)

The [v0.5 verification record](public/verification-v0.5.json) checks a finalized MilestoneBond withdrawal to a reverting EVM receiver, a linked failure log, unchanged receiver balance, and a separate finalized reconciliation restoring the 0.002 test-GEN claim without a duplicate payout. The 0.002 test-GEN reserve was not consumed because the rejected transfer returned its value. The [historical v0.4 record](public/verification.json) reconstructs reserve funding, escrow refund, unused-reserve return and normal payouts on StudioNet; the [v0.3 record](public/verification-v0.3.json) proves the earlier two-stage project. An `ACCEPTED` transaction is still pending until its challenge window closes and separate finalization succeeds.

## Why it exists

One-off bounties pay for one accepted patch. Real projects ship in stages. MilestoneBond makes those stages explicit and sequential. It does not reuse the PatchBond contract or pay on a PR link alone. The sponsor freezes a GitHub issue body hash, repository and base commit, workflow content and identity, author wallet, allowed source paths, criteria, deadlines and per-stage amounts. Later stages cannot submit until earlier ones settle.

## Reviewer path

1. Open the web app. Its hero diagram and walkthrough are illustrative. The Bradbury proof panel links each finalized v0.5 action and its EVM rejection; the v0.4 and v0.3 records are historical.
2. Open **Live projects** and select `MB-BRADBURY-FAIL-001` on the v0.5 Bradbury contract. This expired fixture demonstrates a failed external withdrawal and restored sponsor credit, not a completed software milestone or a second payout. Earlier projects remain on their separate StudioNet contracts and dated records.
3. Open **Create project** to generate terms from a public GitHub issue, commit and workflow, then inspect the JSON and exact deposit before signing. The contract re-fetches the sources; browser-generated hashes alone are not authority.
4. Inspect the [readable v0.5 contract](contracts/milestone_bond_v0_5.py), [exact deployed wrapper](contracts/milestone_bond_v0_5_packed.py), [adversarial tests](tests/direct/test_bradbury_recovery_v05.py), [deployment record](deployments/bradbury_v0.5.json), and [live evidence](docs/BRADBURY_V05_RECOVERY.md).
5. For the v0.3 milestone run, compare the project's onchain criteria and evidence SHA-256 with the pinned GitHub issue, PR head, wallet claim, source and exact CI attempt. Check sponsor approval and validator review. The [steward response](docs/STEWARD_FIXES_V03.md) collects the direct links.

## Local development

Use Python 3.12, Node 24 and pnpm 11:

```sh
python -m pip install -r requirements-dev.txt
genvm-lint check contracts/milestone_bond_v0_4.py --json
genvm-lint check contracts/milestone_bond_v0_5.py --json
genvm-lint check contracts/milestone_bond_v0_5_packed.py --json
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
- Bradbury and StudioNet are test environments; their GEN is not production-value escrow. Use test-only wallets. The [reviewer guide](docs/REVIEW_GUIDE.md) explains wallet funding and the distinct deployments. v0.5 charges a confirmed unreturned loss only to its project's funded reserve, up to the remaining reserve balance; further loss needs sponsor top-up. Ambiguous receipts stay pending. The Bradbury run proves a live external rejection and restored credit, **not** a reserve-consuming loss or a second successful payout. A dated verification record remains historical if a testnet resets.
- There is no background scheduler. Anyone can call the relevant review/finalization or expiry transaction when eligible. A pending review cannot be bypassed by expiry refund.

See [architecture](docs/ARCHITECTURE.md), [deployment guide](docs/DEPLOYMENT.md), [reserve design](docs/V04_RESERVE_DESIGN.md) and [security notes](docs/SECURITY.md). Earlier versions remain retained, but their receipts must not be presented as evidence for protections added later.
