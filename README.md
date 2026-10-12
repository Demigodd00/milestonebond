# MilestoneBond

Ship in public. Pay on proof. MilestoneBond is a standalone GenLayer StudioNet prototype for staged software delivery: a sponsor locks 2–4 fixed tranches, an assigned author submits one PR/commit/CI bundle per stage, and GenLayer validators independently re-fetch the public evidence and agree on every criterion before a tranche is credited. This is **simulated test GEN**, not production escrow or an audit.

[Live app](https://demigodd00.github.io/milestonebond/) · [Dedicated source repository](https://github.com/Demigodd00/milestonebond) · [StudioNet contract](https://explorer-studio.genlayer.com/contracts/0xb437593b7656254226ce496bc6f9A052A11D6345) · [Live two-stage evidence](docs/LIVE_DEMO.md) · [Public demo issue](https://github.com/Demigodd00/milestonebond/issues/1)

The [live verification record](public/verification.json) distinguishes each finalized execution from the contract's application-level stage status. An `ACCEPTED` review is still pending until its challenge window closes and the separate finalization transaction succeeds.

## Why it exists

One-off bounties pay for one accepted patch. Real projects ship in stages. MilestoneBond makes those stages explicit and sequential. It does not reuse the PatchBond contract or pay on a PR link alone. The sponsor freezes a GitHub issue body hash, repository and base commit, workflow content and identity, author wallet, allowed source paths, criteria, deadlines and per-stage amounts. Later stages cannot submit until earlier ones settle.

## Reviewer path

1. Open the web app and follow the clearly labeled simulated walkthrough for the user flow.
2. Open **Live projects** to read the independently deployed StudioNet contract. This view never substitutes simulated data for onchain state.
3. Open **Create project** to generate terms from a public GitHub issue, commit and workflow, then inspect the JSON and exact deposit before signing. The contract re-fetches the sources; browser-generated hashes alone are not authority.
4. Inspect the contract source at `contracts/milestone_bond.py`, the direct tests in `tests/direct`, the [architecture](docs/ARCHITECTURE.md) and [deployment record](deployments/studionet.json) when available.
5. For each submitted milestone, compare the project’s onchain criteria and evidence SHA-256 with the pinned GitHub issue, PR head, source and exact CI attempt. A review is not a payout until its challenge window closes and `finalize_milestone` executes successfully.

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
- GitHub API, the repository owner and GitHub Actions are external trust dependencies. A passing CI run does not prove security or that test criteria were adequate. A sponsor must set meaningful observable criteria and a trustworthy workflow. The prototype supports one direct-child commit per milestone, no forks, and no added/deleted/renamed files.
- StudioNet is a sandbox. Its GEN has no monetary value, its state can be reset, and smart-contract recipient transfer behavior is not guaranteed. Use test-only externally owned wallets. Withdrawals require a separate successful transaction and outbound transfer confirmation.
- There is no background scheduler. Anyone can call the relevant review/finalization or expiry transaction when eligible. A pending review cannot be bypassed by expiry refund.

See [architecture](docs/ARCHITECTURE.md), [deployment guide](docs/DEPLOYMENT.md) and [security notes](docs/SECURITY.md). The first v0.1 StudioNet deployment and its failed project-creation transaction are retained in `deployments/history/` and the live demo journal; v0.2 is the active contract after replacing an oversized GitHub commit response with a bounded metadata endpoint.
