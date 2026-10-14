import {useEffect,useState} from 'react';

type Transaction={method:string;hash:string;url:string;status:string;execution_success:boolean};
type Proof={generated_at:string;contract:string;contract_url:string;source_sha256:string;source_verified:boolean;
  project_id:string;receiver:string;failure:{genlayer_transaction_id:string;evm_finalization_hash:string;
  failure_event_family:string;amount:number;contract_balance_before:number;contract_balance_after:number;
  receiver_balance_before:number;receiver_balance_after:number};
  project_accounting:{claimable:string;reserve_remaining:string;reserve_consumed:string};
  accounting:{pending_withdrawal:unknown;pending_out:string;withdrawn:string};transactions:Transaction[]};
const repo='https://github.com/Demigodd00/milestonebond';
const explorer='https://explorer-bradbury.genlayer.com';
const amount=(atto:string|number)=>`${(Number(BigInt(atto))/1e18).toLocaleString(undefined,{maximumFractionDigits:6})} test GEN`;

function EvidenceLink({href,children}:{href:string;children:React.ReactNode}){
 return <a href={href} target="_blank" rel="noopener noreferrer">{children}<span aria-hidden="true">↗</span></a>;
}

export default function BradburyProofPanel(){
 const [proof,setProof]=useState<Proof|null>(null);
 const [error,setError]=useState('');
 useEffect(()=>{let cancelled=false;fetch(`${import.meta.env.BASE_URL}verification-v0.5.json`,{cache:'no-store'})
  .then(async response=>{if(!response.ok)throw Error(`Evidence record unavailable (${response.status})`);return response.json() as Promise<Proof>})
  .then(value=>{if(!cancelled){const expected=['create_project','recover_expired','withdraw_to','reconcile_withdrawal'];if(!value?.source_verified||value.transactions?.length!==4||!expected.every(method=>value.transactions.some(tx=>tx.method===method&&tx.status==='FINALIZED'&&tx.execution_success))||value.accounting?.pending_withdrawal!==null)throw Error('Incomplete v0.5 evidence record');setProof(value)}})
  .catch(reason=>{if(!cancelled)setError(reason instanceof Error?reason.message:String(reason))});
  return()=>{cancelled=true};},[]);
 const action=(method:string)=>proof?.transactions.find(item=>item.method===method);
 return <section id="bradbury-proof" className="proof-section" aria-labelledby="bradbury-proof-title">
  <div className="proof-heading"><div><span className="section-kicker">V0.5 BRADBURY FAILURE RUN</span><h2 id="bradbury-proof-title">A rejected transfer. A restored claim.</h2></div><span className="proof-state">{proof?`Dated ${new Date(proof.generated_at).toLocaleDateString()}`:'Evidence loading'}</span></div>
  {!proof?<p className="proof-intro" role={error?'alert':undefined}>{error?`The finalized failure evidence cannot be loaded: ${error}. Do not treat this panel as proof.`:'Loading the independently checked Bradbury evidence record…'}</p>:<>
   <p className="proof-intro">The sponsor funded a separate recovery reserve for {proof.project_id}. A {amount(proof.failure.amount)} withdrawal targeted an EVM receiver that always reverts. Bradbury finalized the external failure; the receiver balance stayed unchanged and the contract retained the funds. A separate GenLayer reconciliation restored the sponsor’s claimable credit. No second payout was recorded by this run. This is testnet evidence, not production insurance.</p>
   <div className="proof-steps">
    <article><span>01 / SOURCE</span><h3>Exact release and funded reserve</h3><p>The deployed, hash-checked wrapper resolves to the readable v0.5 contract. The sponsor funded milestone escrow and an equal, project-specific reserve. The fixture expired so its escrow became a sponsor credit.</p><div className="proof-links"><EvidenceLink href={proof.contract_url}>Bradbury contract</EvidenceLink><EvidenceLink href={action('create_project')!.url}>Funding receipt</EvidenceLink><EvidenceLink href={action('recover_expired')!.url}>Expiry receipt</EvidenceLink><EvidenceLink href={`${repo}/blob/main/contracts/milestone_bond_v0_5.py`}>Readable source</EvidenceLink></div></article>
    <article><span>02 / REJECTION</span><h3>External failure, not a mock</h3><p>One native transfer was emitted to {proof.receiver}. The linked EVM finalization contains the {proof.failure.failure_event_family} log. The receiver’s balance remained {amount(proof.failure.receiver_balance_after)} and the contract’s pre/post transfer balance was {amount(proof.failure.contract_balance_after)}.</p><div className="proof-links"><EvidenceLink href={action('withdraw_to')!.url}>GenLayer withdrawal</EvidenceLink><EvidenceLink href={`${explorer}/tx/${proof.failure.evm_finalization_hash}`}>EVM finalization</EvidenceLink><EvidenceLink href={`${explorer}/address/${proof.receiver}`}>Rejecting receiver</EvidenceLink></div></article>
    <article><span>03 / RECONCILIATION</span><h3>Entitlement restored once</h3><p>A separate consensus transaction checked the exact parent call, emitted message, linked finalization and failure log before restoring {amount(proof.project_accounting.claimable)} of credit. Pending withdrawal is cleared. The {amount(proof.project_accounting.reserve_remaining)} reserve was not consumed because the failed transfer returned its value.</p><div className="proof-links"><EvidenceLink href={action('reconcile_withdrawal')!.url}>Recovery receipt</EvidenceLink><EvidenceLink href={`${repo}/blob/main/tests/direct/test_bradbury_recovery_v05.py`}>Adversarial tests</EvidenceLink><EvidenceLink href={`${repo}/blob/main/docs/BRADBURY_V05_RECOVERY.md`}>Evidence and limits</EvidenceLink></div></article>
   </div>
   <div className="proof-sourcebar"><div><strong>Rebuild every claim</strong><small>The public JSON and verification script bind finalized receipts, EVM logs, source hash and latest-final accounting. The restored credit still needs a later valid withdrawal to become a payment.</small></div><div className="proof-links"><EvidenceLink href={`${import.meta.env.BASE_URL}verification-v0.5.json`}>v0.5 verification JSON</EvidenceLink><EvidenceLink href={`${repo}/blob/main/scripts/verify_live_v05.py`}>Verifier script</EvidenceLink><EvidenceLink href={`${repo}/blob/main/deployments/bradbury_v0.5.json`}>Deployment record</EvidenceLink></div></div>
  </>}
 </section>;
}
