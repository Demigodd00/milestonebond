# StudioNet deployment and verification

Run `genvm-lint check contracts/milestone_bond.py --json`, `pytest tests/direct -q`, `pnpm test`, and `pnpm build` first. Then run `python scripts/deploy_studionet.py`. The script creates a disposable deployment-only account, journals the submitted transaction hash, waits for a finalized **successful execution**, reads back deployed source and `get_config`, and writes `deployments/studionet.json` plus the frontend `public/deployment.json`. No private key is persisted.

If deployment stalls or fails, inspect `deployments/pending.json` and its transaction hash before any retry. A finalized transaction may still contain an execution error. Do not delete the journal and redeploy blindly. Source verification is a SHA-256 of normalized line endings; the web app recomputes it before signing.

After deployment, independently check the contract address, transaction receipt, source and ABI on the StudioNet explorer. A live project demonstration requires a real public issue, same-repository PR, exact commit and GitHub Actions run; mocked direct tests are not sufficient. Record the transaction hashes and outcomes in a separate verification report. The frontend walkthrough is simulated and must remain clearly distinct from this live evidence.
