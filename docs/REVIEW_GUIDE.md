# MilestoneBond reviewer guide

MilestoneBond is a standalone, test-only GenLayer app for staged software delivery. A sponsor funds 2–4 fixed tranches; the assigned author submits a public PR, exact commit and CI attempt for each stage. Validators independently re-fetch the frozen GitHub evidence and compare per-criterion conclusions before the contract can credit a tranche. It is not audited or suitable for real-value escrow.

## Start here — no wallet needed

1. [Open the app](https://demigodd00.github.io/milestonebond/). The hero diagram and guided walkthrough are explicitly illustrative. Select **Verify the live run** for the actual two-stage StudioNet case.
2. Select **Live projects** and open `MB-LIVE-001`. This view reads finalized state from the deployed contract. The **initial frozen base** is shown separately from the **latest accepted head** that advances after each payout.
3. [Read the dated verification record](https://demigodd00.github.io/milestonebond/verification.json), then compare it with the [contract on the StudioNet explorer](https://explorer-studio.genlayer.com/contracts/0xb437593b7656254226ce496bc6f9A052A11D6345). A dated record is not a substitute for current chain state; StudioNet may reset.
4. Follow the [full transaction timeline](LIVE_DEMO.md): both reviews, both stage finalizations, author withdrawal and the separate outbound native transfer. Stage two had three agreeing validator votes, one dissent and one idle vote; no unanimity is claimed.

## Public evidence

- [Dedicated source repository](https://github.com/Demigodd00/milestonebond) and [intelligent contract](../contracts/milestone_bond.py)
- [Frozen issue #1](https://github.com/Demigodd00/milestonebond/issues/1), [stage 1 PR #2](https://github.com/Demigodd00/milestonebond/pull/2), [stage 2 PR #3](https://github.com/Demigodd00/milestonebond/pull/3)
- [Stage 1 CI](https://github.com/Demigodd00/milestonebond/actions/runs/38197462942) and [stage 2 CI](https://github.com/Demigodd00/milestonebond/actions/runs/38198377989)
- [Stage 1 review receipt](https://explorer-studio.genlayer.com/transactions/0x62f9e7196b70de52e337a6292705a1b80bad83383fa7cfe7dc3a359c3eeed842) and [stage 2 review receipt](https://explorer-studio.genlayer.com/transactions/0x01a1a6dbf1fc9133fbdc3e22fe1c543151c7c8b27375b24e8c8d2b4be80bfc80)
- [Final outbound transfer receipt](https://explorer-studio.genlayer.com/transactions/0x70483e221fabdc080bc6e476610cc103fdbb668303bd155032890d70ff353944)

The active v0.2 source SHA-256 is `15085f0aba712bbacb1d99713be343aa551f19dc3b6ae02004fd8afca6c16d4f` after LF line-ending normalization. The v0.1 failed attempt is disclosed in the [timeline](LIVE_DEMO.md); it was not on the active contract.

## Try the signing path

Use a test-only EIP-1193 browser wallet on StudioNet, chain ID `61999`. GenLayer Studio has a built-in faucet in its account selector; verify that the **same address** connected to MilestoneBond has enough simulated GEN for the full deposit before signing. The app checks that balance and shows the exact deposit. The [GenLayer network guide](https://docs.genlayer.com/developers/networks) describes StudioNet and its faucet. The public completed demo can be inspected without a wallet or funding.

The app stores the returned transaction hash, polls that exact hash through consensus, and checks execution success after finalization. The repository tests cover wallet connection and receipt parsing with mocks; the historical live receipts prove the contract workflow, not that an arbitrary reviewer wallet has completed a new end-to-end browser signing session.

StudioNet is temporary. If the live project disappears after a network reset, the archived JSON and transaction links document the historical run, but they must not be presented as current onchain state. A persistent Bradbury deployment would be a separate release with a new address and proof package.
