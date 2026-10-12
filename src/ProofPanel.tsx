const repo = 'https://github.com/Demigodd00/milestonebond';
const explorer = 'https://explorer-studio.genlayer.com';
const demoContract = '0xb437593b7656254226ce496bc6f9A052A11D6345';
const reviewOne = '0x62f9e7196b70de52e337a6292705a1b80bad83383fa7cfe7dc3a359c3eeed842';
const reviewTwo = '0x01a1a6dbf1fc9133fbdc3e22fe1c543151c7c8b27375b24e8c8d2b4be80bfc80';
const withdrawal = '0x27a52ade9f9edbfc017490adecd488273f6a89394b016d83dd267563a1b5a355';
const transfer = '0x70483e221fabdc080bc6e476610cc103fdbb668303bd155032890d70ff353944';

function EvidenceLink({href,children}:{href:string;children:React.ReactNode}) {
  return <a href={href} target="_blank" rel="noopener noreferrer">{children}<span aria-hidden="true">↗</span></a>;
}

export default function ProofPanel({liveStatus,readReady}:{liveStatus?:string;readReady:boolean}) {
  return <section id="proof" className="proof-section" aria-labelledby="proof-title">
    <div className="proof-heading">
      <div><span className="section-kicker">VERIFY THE LIVE RUN</span><h2 id="proof-title">Two stages. Two verdicts. One settled payout.</h2></div>
      <span className="proof-state">{liveStatus ? `Latest onchain read: ${liveStatus.replaceAll('_',' ')}` : readReady ? 'No current onchain demo; archived record only' : 'Live state: loading or unavailable'}</span>
    </div>
    <p className="proof-intro">The walkthrough is illustrative. This is the separate public StudioNet record for project MB-LIVE-001: each stage was reviewed, finalized, and paid in simulated GEN. Stage two reached consensus with three agreeing validators, one dissent and one idle validator—not unanimity.</p>
    <div className="proof-steps">
      <article><span>01 / SOURCE</span><h3>Frozen public work</h3><p>Inspect the issue, the exact PR heads and their passing CI runs.</p><div className="proof-links"><EvidenceLink href={`${repo}/issues/1`}>Issue #1</EvidenceLink><EvidenceLink href={`${repo}/pull/2`}>Stage 1 PR</EvidenceLink><EvidenceLink href={`${repo}/actions/runs/38197462942`}>Stage 1 CI</EvidenceLink><EvidenceLink href={`${repo}/pull/3`}>Stage 2 PR</EvidenceLink><EvidenceLink href={`${repo}/actions/runs/38198377989`}>Stage 2 CI</EvidenceLink></div></article>
      <article><span>02 / CONSENSUS</span><h3>Independent reviews</h3><p>Read the finalized review transactions, including validator votes and the stage-two dissent.</p><div className="proof-links"><EvidenceLink href={`${explorer}/transactions/${reviewOne}`}>Stage 1 receipt</EvidenceLink><EvidenceLink href={`${explorer}/transactions/${reviewTwo}`}>Stage 2 receipt</EvidenceLink></div></article>
      <article><span>03 / SETTLEMENT</span><h3>Native transfer confirmed</h3><p>The separate withdrawal and outbound transfer completed for 0.002 simulated test GEN.</p><div className="proof-links"><EvidenceLink href={`${explorer}/transactions/${withdrawal}`}>Withdrawal receipt</EvidenceLink><EvidenceLink href={`${explorer}/transactions/${transfer}`}>Transfer receipt</EvidenceLink><EvidenceLink href={`${explorer}/contracts/${demoContract}`}>Contract</EvidenceLink></div></article>
    </div>
    <div className="proof-sourcebar"><div><strong>Audit the full trail</strong><small>The verification JSON is a dated snapshot, not a substitute for current onchain state. StudioNet may reset.</small></div><div className="proof-links"><EvidenceLink href={`${import.meta.env.BASE_URL}verification.json`}>Verification record</EvidenceLink><EvidenceLink href={`${repo}/blob/main/docs/LIVE_DEMO.md`}>Transaction timeline</EvidenceLink><EvidenceLink href={`${repo}/blob/main/docs/REVIEW_GUIDE.md`}>Reviewer guide</EvidenceLink><EvidenceLink href={repo}>Source repository</EvidenceLink></div></div>
  </section>;
}
