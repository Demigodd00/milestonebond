const explorer = 'https://explorer-studio.genlayer.com';
const contract = '0x9218b57964ae4eBe9c9756bb48b3454a03Ce707D';
const proof = {
  fund:'0xf5c4427ca68d610325a7c558719fb0d957dfc108a6607a9cca37c1e072f93adb',
  expire:'0xe6cd0d0c2b9a0a904d1884c33207716fb41f6a1ab869d3cbb1cec642ada51004',
  escrowWithdraw:'0x4847157a3c1a2951142b2c72ad29c7c95defdff9e7d87b311c0d6d1cf82693bd',
  escrowChild:'0x0056b3871001874804ca47cfacabde4d9eeb550a187c3c16ff7a6d9eda80a848',
  escrowReconcile:'0xd096eb857a96dc43947d2fb77a14e3e42ac4661631fbd0c82c6a4ca24f03a83c',
  release:'0x1fb4ce4c73b08a046a81a75d090a4653bc345dcf7f05af5a55fcae5973de04f9',
  reserveWithdraw:'0xc3a2c97619454dbf7c7112b48d36a944f4a6aa3c84a68d57920069f4ddf44698',
  reserveChild:'0x8277ce3ad50981cceb1897b7783ad8807dc51f6c1def41e42c8b6918b236b975',
  reserveReconcile:'0xb2944c56b255ee0b1ecb666a0e930215f77c69e46e34709e7b3dae1cb85ffd08',
};
const receipt = (hash:string)=>`${explorer}/transactions/${hash}`;

function EvidenceLink({href,children}:{href:string;children:React.ReactNode}) {
  return <a href={href} target="_blank" rel="noopener noreferrer">{children}<span aria-hidden="true">↗</span></a>;
}

export default function ReserveProofPanel({status}:{status?:string}) {
  return <section id="reserve-proof" className="proof-section" aria-labelledby="reserve-proof-title">
    <div className="proof-heading">
      <div><span className="section-kicker">V0.4 RESERVE RUN</span><h2 id="reserve-proof-title">Sponsor-funded protection. Unused reserve returned.</h2></div>
      <span className="proof-state">{status ? `Latest onchain read: ${status.replaceAll('_',' ')}` : 'See dated verification record'}</span>
    </div>
    <p className="proof-intro">The v0.4 StudioNet fixture funds 0.002 simulated GEN of milestone escrow and a separate 0.002 reserve. After author acceptance expires, the sponsor recovers the escrow, reconciles its native payout, releases the untouched reserve, and reconciles that second payout. The reserve is project-specific and cannot be released while its project has unpaid claims.</p>
    <div className="proof-steps">
      <article><span>01 / FUND</span><h3>Two distinct balances</h3><p>The sponsor deposits twice the milestone budget. Half funds milestones; half is locked as that project’s finite recovery reserve.</p><div className="proof-links"><EvidenceLink href={receipt(proof.fund)}>Funding receipt</EvidenceLink><EvidenceLink href={`${explorer}/contracts/${contract}`}>v0.4 contract</EvidenceLink><EvidenceLink href="https://github.com/Demigodd00/milestonebond/blob/main/contracts/milestone_bond_v0_4.py">Pinned source</EvidenceLink></div></article>
      <article><span>02 / RECONCILE</span><h3>Claims before refund</h3><p>Expiry credits the sponsor’s escrow refund. A finalized parent alone is not payment: its exact native child must be credited and reconciled before the reserve is releasable.</p><div className="proof-links"><EvidenceLink href={receipt(proof.expire)}>Expiry refund</EvidenceLink><EvidenceLink href={receipt(proof.escrowWithdraw)}>Withdrawal</EvidenceLink><EvidenceLink href={receipt(proof.escrowChild)}>Credited child</EvidenceLink><EvidenceLink href={receipt(proof.escrowReconcile)}>Reconciliation</EvidenceLink></div></article>
      <article><span>03 / RETURN</span><h3>Unused reserve to sponsor</h3><p>One release creates sponsor credit, then a second native withdrawal pays it. Direct adversarial tests exercise uncredited child outcomes; StudioNet has not produced a live uncredited external child.</p><div className="proof-links"><EvidenceLink href={receipt(proof.release)}>Reserve release</EvidenceLink><EvidenceLink href={receipt(proof.reserveWithdraw)}>Withdrawal</EvidenceLink><EvidenceLink href={receipt(proof.reserveChild)}>Credited child</EvidenceLink><EvidenceLink href={receipt(proof.reserveReconcile)}>Reconciliation</EvidenceLink><EvidenceLink href="https://github.com/Demigodd00/milestonebond/blob/main/tests/direct/test_reserve_v04.py">Adversarial tests</EvidenceLink><EvidenceLink href="https://github.com/Demigodd00/milestonebond/blob/main/docs/V04_RESERVE_DESIGN.md">Coverage limits</EvidenceLink></div></article>
    </div>
    <div className="proof-sourcebar"><div><strong>Rebuild the record</strong><small>The JSON checks deployed source, finalized receipts, linked children and final accounting. It is a dated snapshot; StudioNet can reset.</small></div><div className="proof-links"><EvidenceLink href={`${import.meta.env.BASE_URL}verification.json`}>v0.4 verification JSON</EvidenceLink><EvidenceLink href="https://github.com/Demigodd00/milestonebond/blob/main/deployments/studionet_v0.4.json">Deployment record</EvidenceLink></div></div>
  </section>;
}
