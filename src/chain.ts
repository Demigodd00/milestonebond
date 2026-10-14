import {createClient,chains} from 'genlayer-js';
import {TransactionHashVariant,type Hash} from 'genlayer-js/types';

export type Provider={request(args:{method:string;params?:unknown[]}):Promise<unknown>};
export type Session={address:`0x${string}`;provider:Provider};
export type Deployment={verified:boolean;address:string|null;chainId:number;sourceSha256:string;version:string;network:string};
export type Pending={hash:`0x${string}`;method:string;projectId:string;address:string;account:string;submittedAt:number};
export const pendingKey='milestonebond:pending:v0.4:61999';
export const pendingKeyFor=(d:Deployment)=>d.version==='milestonebond.v0.5'?'milestonebond:pending:v0.5:4221':pendingKey;
const chainFor=(d?:Deployment)=>d?.network==='bradbury'&&d.chainId===4221?chains.testnetBradbury:chains.studionet;
const readerFor=(d?:Deployment)=>createClient({chain:chainFor(d)});
let inFlight=false;
const hashPattern=/^0x[0-9a-fA-F]{64}$/;
const bradburyMain='0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D';
const finalizedTopic='0x24196ec40f90671b7144e716978686b4f3c7d6b00b23da3971ef2b52af27d87f';

async function chainRpc<T>(method:string,params:unknown[]):Promise<T>{
 const response=await fetch('https://rpc.testnet-chain.genlayer.com',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params})});
 if(!response.ok)throw Error(`Bradbury chain RPC unavailable (${response.status}).`);
 const payload=await response.json() as {result?:T;error?:{message?:string}};
 if(payload.error||payload.result===undefined)throw Error(`Bradbury chain RPC: ${payload.error?.message||'missing result'}`);
 return payload.result;
}

async function genRpc<T>(method:string,params:unknown[]):Promise<T>{
 const response=await fetch('https://rpc-bradbury.genlayer.com',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params})});
 if(!response.ok)throw Error(`Bradbury GenLayer RPC unavailable (${response.status}).`);
 const payload=await response.json() as {result?:T;error?:{message?:string}};
 if(payload.error||payload.result==null)throw Error(`Bradbury GenLayer RPC: ${payload.error?.message||'transaction not found'}`);
 return payload.result;
}

export async function findFinalization(parentHash:string):Promise<`0x${string}`|null>{
 if(!hashPattern.test(parentHash))throw Error('Enter a full GenLayer withdrawal transaction ID.');
 const latest=BigInt(await chainRpc<string>('eth_blockNumber',[]));
 const from=latest>9999n?latest-9999n:0n;
 const logs=await chainRpc<Array<{address:string;topics:string[];transactionHash:string}>>('eth_getLogs',[{address:bradburyMain,fromBlock:'0x'+from.toString(16),toBlock:'latest',topics:[finalizedTopic,parentHash]}]);
 const matches=logs.filter(log=>log.address.toLowerCase()===bradburyMain.toLowerCase()&&log.topics.length===2&&log.topics[0]?.toLowerCase()===finalizedTopic&&log.topics[1]?.toLowerCase()===parentHash.toLowerCase()&&hashPattern.test(log.transactionHash));
 if(matches.length>1)throw Error('Multiple finalization events matched; inspect the explorer before reconciling.');
 return matches.length===1?matches[0].transactionHash as `0x${string}`:null;
}

export async function deployment():Promise<Deployment>{
 const response=await fetch(`${import.meta.env.BASE_URL}deployment.json`,{cache:'no-store'});
 if(!response.ok)throw Error('Deployment record is unavailable.');
 return response.json() as Promise<Deployment>;
}
export async function read<T>(d:Deployment,method:string,args:unknown[]=[]):Promise<T>{
 if(!d.verified||!d.address)throw Error('No verified live deployment is configured.');
 const value=await readerFor(d).readContract({address:d.address as `0x${string}`,functionName:method,args:args as never[],transactionHashVariant:TransactionHashVariant.LATEST_FINAL});
 return JSON.parse(JSON.stringify(value,(_,v)=>typeof v==='bigint'?v.toString():v)) as T;
}
export async function verifyDeployment(d:Deployment){
 const supported=(d.chainId===61999&&d.network==='studionet'&&['milestonebond.v0.3','milestonebond.v0.4'].includes(d.version))||(d.chainId===4221&&d.network==='bradbury'&&d.version==='milestonebond.v0.5');
 if(!d.verified||!/^0x[0-9a-fA-F]{40}$/.test(d.address||'')||!supported||!/^([0-9a-f]{64})$/.test(d.sourceSha256))throw Error('Live signing is disabled until the supported contract is verified.');
 const config=await read<{version:string;challenge_seconds:number;fee_bps:number;delivery_policy:string;reserve_policy?:string;network_scope?:string;settlement_proof?:string}>(d,'get_config');
 if(config.version!==d.version||config.delivery_policy!=='SPONSOR_APPROVED_UNMERGED_COMMIT'||Number(config.challenge_seconds)!==600||Number(config.fee_bps)!==0)throw Error('Onchain policy differs from this release.');
 if(['milestonebond.v0.4','milestonebond.v0.5'].includes(d.version)&&config.reserve_policy!=='SPONSOR_FUNDS_100_PERCENT_OF_MILESTONE_BUDGET_REFUND_UNUSED_AFTER_CLAIMS')throw Error('Onchain reserve policy differs from this release.');
 if(d.version==='milestonebond.v0.5'&&(config.network_scope!=='bradbury-testnet-only'||config.settlement_proof!=='GEN_RECEIPT_MESSAGE_AND_EVM_FINALIZATION'))throw Error('Onchain settlement policy differs from this release.');
 const code=await readerFor(d).getContractCode(d.address as `0x${string}`);
 const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(code.replaceAll('\r\n','\n')));
 const digest=[...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,'0')).join('');
 if(digest!==d.sourceSha256)throw Error('Onchain source differs from this release. Signing blocked.');
}
export async function connect(d?:Deployment):Promise<Session>{
 const p=(window as unknown as {ethereum?:Provider}).ethereum;
 if(!p)throw Error('Install or unlock an EVM wallet to sign testnet transactions.');
 const addresses=await p.request({method:'eth_requestAccounts'}) as string[];
 if(!/^0x[0-9a-fA-F]{40}$/.test(addresses?.[0]||''))throw Error('No wallet account selected.');
 const chain=chainFor(d);
 if(Number(await p.request({method:'eth_chainId'}))!==chain.id){
  try{await p.request({method:'wallet_switchEthereumChain',params:[{chainId:'0x'+chain.id.toString(16)}]});}
  catch(e){if((e as {code?:number}).code!==4902)throw e;await p.request({method:'wallet_addEthereumChain',params:[{chainId:'0x'+chain.id.toString(16),chainName:chain.name,nativeCurrency:chain.nativeCurrency,rpcUrls:chain.rpcUrls.default.http,blockExplorerUrls:[d?.network==='bradbury'?'https://explorer-bradbury.genlayer.com':'https://explorer-studio.genlayer.com']}]});}
 }
 if(d?.network==='bradbury'&&d.address){const code=await p.request({method:'eth_getCode',params:[d.address,'latest']});if(typeof code!=='string'||code==='0x'||code==='0x0')throw Error('Wallet is not connected to the Bradbury chain containing this contract. Check its RPC, even if chain ID 4221 matches.');}
 return {address:addresses[0].toLowerCase() as `0x${string}`,provider:p};
}
async function verifySession(s:Session,d:Deployment){
 const accounts=await s.provider.request({method:'eth_accounts'}) as string[];
 if(accounts?.[0]?.toLowerCase()!==s.address||Number(await s.provider.request({method:'eth_chainId'}))!==d.chainId)throw Error('Wallet account or network changed; reconnect before signing.');
 if(d.network==='bradbury'){const code=await s.provider.request({method:'eth_getCode',params:[d.address,'latest']});if(typeof code!=='string'||code==='0x'||code==='0x0')throw Error('Wallet is not on the Bradbury chain containing this contract.');}
}
export function receiptOutcome(receipt:unknown):'pending'|'success'|'error'{
 if(!receipt||typeof receipt!=='object')return 'pending';
 const r=receipt as Record<string,unknown>;
 if(typeof r.status==='number'){
  if(r.status===8)return 'error';
  if(r.status!==7)return 'pending';
  return r.txExecutionResult===1?'success':r.txExecutionResult===2?'error':'pending';
 }
 const status=String(r.statusName??r.status_name??r.status??'').toUpperCase();
 if(['CANCELED','CANCELLED','DROPPED'].includes(status))return 'error';
 if(status!=='FINALIZED')return 'pending';
 const data=(r.consensusData??r.consensus_data) as Record<string,unknown>|undefined;
 const raw=data?.leaderReceipt??data?.leader_receipt;
 const leader=(Array.isArray(raw)?[...raw].reverse().find(x=>x?.mode==='leader')??raw.at(-1):raw) as Record<string,unknown>|undefined;
 const execution=String(leader?.executionResult??leader?.execution_result??'').toUpperCase();
 const normalized=String(r.txExecutionResultName??r.tx_execution_result_name??'').toUpperCase();
 if(['ERROR','FAILURE','VM_ERROR'].includes(execution)||normalized==='FINISHED_WITH_ERROR')return 'error';
 return execution==='SUCCESS'||normalized==='FINISHED_WITH_RETURN'?'success':'pending';
}
export async function poll(p:Pending,d:Deployment){
 if(!hashPattern.test(p.hash))throw Error('Invalid saved transaction hash.');
 if(p.address.toLowerCase()!==d.address?.toLowerCase())throw Error('Pending transaction targets a different deployment.');
 const raw=d.network==='bradbury'?await genRpc<unknown>('gen_getTransactionReceipt',[{txId:p.hash}]):await readerFor(d).getTransaction({hash:p.hash as Hash});
 const result=receiptOutcome(raw);
 if(result!=='pending'){
  const key=pendingKeyFor(d),saved=localStorage.getItem(key);
  if(saved&&JSON.parse(saved).hash===p.hash)localStorage.removeItem(key);
 }
 return result;
}
export async function send(d:Deployment,s:Session,method:string,args:unknown[],value:bigint,onHash:(p:Pending)=>void){
 const arities:Record<string,number>={create_project:1,accept_project:1,submit_milestone:5,approve_submission:3,review_milestone:2,challenge_review:3,finalize_milestone:1,recover_expired:1,withdraw:d.version==='milestonebond.v0.3'?1:2,reconcile_withdrawal:d.version==='milestonebond.v0.5'?2:1,top_up_recovery:0,...(['milestonebond.v0.4','milestonebond.v0.5'].includes(d.version)?{release_reserve:1}:{})};
 if(d.version==='milestonebond.v0.5')arities.withdraw_to=3;
 if(!(method in arities)||args.length!==arities[method]||(!['create_project','top_up_recovery'].includes(method)&&value!==0n))throw Error('Invalid contract action.');
 if(!navigator.locks)throw Error('A current browser with Web Locks is required for safe signing.');
 const key=pendingKeyFor(d);
 return navigator.locks.request(`milestonebond:sign:${d.chainId}`,{ifAvailable:true},async lock=>{
  if(!lock||inFlight||localStorage.getItem(key))throw Error('A transaction is already pending. Resolve it before signing again.');
  inFlight=true;let requested=false;let known:Pending|undefined;
  try{
   const active=await deployment();
   if(active.address!==d.address||active.sourceSha256!==d.sourceSha256||!active.verified)throw Error('Deployment changed; reload.');
   await verifyDeployment(d);await verifySession(s,d);
   if(method==='create_project'&&await readerFor(d).getBalance({address:s.address})<value)throw Error('Insufficient testnet GEN.');
   localStorage.setItem(key+':probe','1');localStorage.removeItem(key+':probe');
   const guarded:Provider={request:async request=>{
    if(!['eth_sendTransaction','eth_sendRawTransaction','eth_signTransaction'].includes(request.method))return s.provider.request(request);
    if(requested)throw Error('A duplicate wallet submission was blocked. Check wallet Activity.');
    requested=true;const result=await s.provider.request(request);
    if(request.method!=='eth_signTransaction'&&typeof result==='string'&&hashPattern.test(result))remember(result as `0x${string}`);
    return result;
   }};
   const remember=(hash:`0x${string}`)=>{
    if(known){if(known.hash!==hash)throw Error('Conflicting transaction hashes.');return;}
    known={hash,method,projectId:method==='create_project'?JSON.parse(String(args[0])).id:String(args[0]??''),address:d.address!,account:s.address,submittedAt:Date.now()};
    localStorage.setItem(key,JSON.stringify(known));onHash(known);
   };
   const writer=createClient({chain:chainFor(d),account:s.address,provider:guarded as never});
   const hash=await writer.writeContract({address:d.address as `0x${string}`,functionName:method,args:args as never[],value});
   if(typeof hash!=='string'||!hashPattern.test(hash))throw Error('No valid transaction hash returned.');
   remember(hash as `0x${string}`);
   return known!;
  }catch(error){
   if(known)throw Error(`Transaction ${known.hash} was submitted. Check its result before retrying. ${String(error)}`);
   if(requested)throw Error(`Wallet submission status is unknown. Check wallet Activity before manually retrying. ${String(error)}`);
   throw error;
  }finally{inFlight=false;}
 });
}
