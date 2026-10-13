const repo = 'https://github.com/Demigodd00/milestonebond';
const explorer = 'https://explorer-studio.genlayer.com';
const contract = '0xa3Cb18a9846a49aF882Cae38fB79923D7F6DcC34';
const stageOneReview = '0x3e27b4a6b6ac2611ebee04429589cd30f52e5457eead35a20acb8614f62a7a76';
const stageTwoRejected = '0xd1c88b2c056618f8f3a6171541bbf8f50905250b4a5876ee31c98cf119661160';
const stageTwoApproval = '0x11e74569502749005610b631e4e0dcd3e014d377412df840018ce57897aa4969';
const stageTwoReview = '0x4624fc0c274e0089b8757295c0f89c4528d6d8f72dffcd58b8c43cbcb1968e99';
const stageTwoFinal = '0xd8900d7a74d0c51e5e5d3b82dc57820e7c17d395a08c4819d21bd23b63f2db13';
const withdrawal = '0x2eb73e68d42db8fc74a2f5e44372f0dd86da65a5d23d6ceeffb88c96ac6faac6';
const transfer = '0xf8d01660e706e44d976cedc5c612156d8dd3a6f0307ff802aa3ab6e67f6c14bc';
const wrongParent = '0x266314bedf989710d5412a7b807a2eb716947dc7d7fbe4f91bf30349e55ea726';
const reconciliation = '0x09c68d91a3800464fec4cdf55d2384c92cc805f0044e31ce04d6d8f81baa9c6a';

function EvidenceLink({href,children}:{href:string;children:React.ReactNode}) {
  return <a href={href} target="_blank" rel="noopener noreferrer">{children}<span aria-hidden="true">↗</span></a>;
}

export default function ProofPanel() {
  return <section id="proof" className="proof-section" aria-labelledby="proof-title">
    <div className="proof-heading">
      <div><span className="section-kicker">VERIFIED V0.3 RUN</span><h2 id="proof-title">Two approved stages. One reconciled payout.</h2></div>
      <span className="proof-state">Archived v0.3 record; separate contract</span>
    </div>
    <p className="proof-intro">The walkthrough is illustrative. This is the separate v0.3 StudioNet record for MB-LIVE-002: both unmerged commits were claimed by the assigned wallet, approved by the sponsor, reviewed by validators, and finally settled. A wrong-parent reconciliation failed before the exact linked native transfer was reconciled. This is simulated GEN, not production escrow.</p>
    <div className="proof-steps">
      <article><span>01 / SOURCE</span><h3>Frozen public work</h3><p>Inspect the issue, exact PR heads, wallet claims and fresh CI attempts. The policy is sponsor-approved unmerged delivery—not a claim of merged code.</p><div className="proof-links"><EvidenceLink href={`${repo}/issues/1`}>Issue #1</EvidenceLink><EvidenceLink href={`${repo}/pull/2`}>Stage 1 PR</EvidenceLink><EvidenceLink href={`${repo}/actions/runs/38197462942/attempts/2`}>Stage 1 CI attempt 2</EvidenceLink><EvidenceLink href={`${repo}/pull/3`}>Stage 2 PR</EvidenceLink><EvidenceLink href={`${repo}/actions/runs/38198377989/attempts/2`}>Stage 2 CI attempt 2</EvidenceLink></div></article>
      <article><span>02 / CONSENSUS</span><h3>Approval gate enforced</h3><p>Stage two first tried review without sponsor approval and finalized with an execution error. Only the later exact-hash approval unlocked validator review and eventual finalization.</p><div className="proof-links"><EvidenceLink href={`${explorer}/transactions/${stageOneReview}`}>Stage 1 receipt</EvidenceLink><EvidenceLink href={`${explorer}/transactions/${stageTwoRejected}`}>Premature review rejected</EvidenceLink><EvidenceLink href={`${explorer}/transactions/${stageTwoApproval}`}>Sponsor approval</EvidenceLink><EvidenceLink href={`${explorer}/transactions/${stageTwoReview}`}>Stage 2 receipt</EvidenceLink><EvidenceLink href={`${explorer}/transactions/${stageTwoFinal}`}>Stage 2 finalization</EvidenceLink></div></article>
      <article><span>03 / SETTLEMENT</span><h3>Native transfer reconciled</h3><p>The 0.002 test-GEN withdrawal stayed pending until its exact child finalized with <code>value_credited=true</code>. A wrong-parent attempt failed and did not clear the entitlement; the correct reconciliation recorded the payout once.</p><div className="proof-links"><EvidenceLink href={`${explorer}/transactions/${withdrawal}`}>Withdrawal receipt</EvidenceLink><EvidenceLink href={`${explorer}/transactions/${transfer}`}>Transfer receipt</EvidenceLink><EvidenceLink href={`${explorer}/transactions/${wrongParent}`}>Wrong parent rejected</EvidenceLink><EvidenceLink href={`${explorer}/transactions/${reconciliation}`}>Reconciliation receipt</EvidenceLink><EvidenceLink href={`${explorer}/contracts/${contract}`}>v0.3 contract</EvidenceLink></div></article>
    </div>
    <div className="proof-sourcebar"><div><strong>Audit the full trail</strong><small>The verification JSON is a dated snapshot, not a substitute for current onchain state. StudioNet may reset.</small></div><div className="proof-links"><EvidenceLink href={`${import.meta.env.BASE_URL}verification-v0.3.json`}>v0.3 verification record</EvidenceLink><EvidenceLink href={`${repo}/blob/main/docs/STEWARD_FIXES_V03.md`}>Steward response</EvidenceLink><EvidenceLink href={`${import.meta.env.BASE_URL}verification-v0.2.json`}>Historical v0.2 record</EvidenceLink><EvidenceLink href={repo}>Source repository</EvidenceLink></div></div>
  </section>;
}
