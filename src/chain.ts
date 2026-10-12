import {createClient,chains} from 'genlayer-js';
import {TransactionHashVariant,type Hash} from 'genlayer-js/types';

export type Provider={request(args:{method:string;params?:unknown[]}):Promise<unknown>};
export type Session={address:`0x${string}`;provider:Provider};
export type Deployment={verified:boolean;address:string|null;chainId:number;sourceSha256:string;version:string;network:string};
export type Pending={hash:`0x${string}`;method:string;projectId:string;address:string;account:string;submittedAt:number};
export const pendingKey='milestonebond:pending:61999';
const reader=createClient({chain:chains.studionet});
let inFlight=false;
const hashPattern=/^0x[0-9a-fA-F]{64}$/;

export async function deployment():Promise<Deployment>{
 const response=await fetch(`${import.meta.env.BASE_URL}deployment.json`,{cache:'no-store'});
 if(!response.ok)throw Error('Deployment record is unavailable.');
 return response.json() as Promise<Deployment>;
}
export async function read<T>(d:Deployment,method:string,args:unknown[]=[]):Promise<T>{
 if(!d.verified||!d.address)throw Error('No verified live deployment is configured.');
 const value=await reader.readContract({address:d.address as `0x${string}`,functionName:method,args:args as never[],transactionHashVariant:TransactionHashVariant.LATEST_FINAL});
 return JSON.parse(JSON.stringify(value,(_,v)=>typeof v==='bigint'?v.toString():v)) as T;
}
export async function verifyDeployment(d:Deployment){
 if(!d.verified||!/^0x[0-9a-fA-F]{40}$/.test(d.address||'')||d.chainId!==61999||d.network!=='studionet'||d.version!=='milestonebond.v0.1'||!/^([0-9a-f]{64})$/.test(d.sourceSha256))throw Error('Live signing is disabled until the StudioNet contract is verified.');
 const config=await read<{version:string;challenge_seconds:number;fee_bps:number}>(d,'get_config');
 if(config.version!==d.version||Number(config.challenge_seconds)!==600||Number(config.fee_bps)!==0)throw Error('Onchain policy differs from this release.');
 const code=await reader.getContractCode(d.address as `0x${string}`);
 const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(code.replaceAll('\r\n','\n')));
 const digest=[...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,'0')).join('');
 if(digest!==d.sourceSha256)throw Error('Onchain source differs from this release. Signing blocked.');
}
export async function connect():Promise<Session>{
 const p=(window as unknown as {ethereum?:Provider}).ethereum;
 if(!p)throw Error('Install or unlock an EVM wallet to sign StudioNet transactions.');
 const addresses=await p.request({method:'eth_requestAccounts'}) as string[];
 if(!/^0x[0-9a-fA-F]{40}$/.test(addresses?.[0]||''))throw Error('No wallet account selected.');
 const chain=chains.studionet;
 if(Number(await p.request({method:'eth_chainId'}))!==chain.id){
  try{await p.request({method:'wallet_switchEthereumChain',params:[{chainId:'0x'+chain.id.toString(16)}]});}
  catch(e){if((e as {code?:number}).code!==4902)throw e;await p.request({method:'wallet_addEthereumChain',params:[{chainId:'0x'+chain.id.toString(16),chainName:chain.name,nativeCurrency:chain.nativeCurrency,rpcUrls:chain.rpcUrls.default.http,blockExplorerUrls:['https://explorer-studio.genlayer.com']}]});}
 }
 return {address:addresses[0].toLowerCase() as `0x${string}`,provider:p};
}
async function verifySession(s:Session){
 const accounts=await s.provider.request({method:'eth_accounts'}) as string[];
 if(accounts?.[0]?.toLowerCase()!==s.address||Number(await s.provider.request({method:'eth_chainId'}))!==61999)throw Error('Wallet account or network changed; reconnect before signing.');
}
export function receiptOutcome(receipt:unknown):'pending'|'success'|'error'{
 if(!receipt||typeof receipt!=='object')return 'pending';
 const r=receipt as Record<string,unknown>;
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
export async function poll(p:Pending){
 if(!hashPattern.test(p.hash))throw Error('Invalid saved transaction hash.');
 const result=receiptOutcome(await reader.getTransaction({hash:p.hash as Hash}));
 if(result!=='pending'){
  const saved=localStorage.getItem(pendingKey);
  if(saved&&JSON.parse(saved).hash===p.hash)localStorage.removeItem(pendingKey);
 }
 return result;
}
export async function send(d:Deployment,s:Session,method:string,args:unknown[],value:bigint,onHash:(p:Pending)=>void){
 const arities:Record<string,number>={create_project:1,accept_project:1,submit_milestone:5,review_milestone:2,challenge_review:3,finalize_milestone:1,recover_expired:1,withdraw:0};
 if(!(method in arities)||args.length!==arities[method]||(method!=='create_project'&&value!==0n))throw Error('Invalid contract action.');
 if(!navigator.locks)throw Error('A current browser with Web Locks is required for safe signing.');
 return navigator.locks.request('milestonebond:sign:61999',{ifAvailable:true},async lock=>{
  if(!lock||inFlight||localStorage.getItem(pendingKey))throw Error('A transaction is already pending. Resolve it before signing again.');
  inFlight=true;let requested=false;let known:Pending|undefined;
  try{
   const active=await deployment();
   if(active.address!==d.address||active.sourceSha256!==d.sourceSha256||!active.verified)throw Error('Deployment changed; reload.');
   await verifyDeployment(d);await verifySession(s);
   if(method==='create_project'&&await reader.getBalance({address:s.address})<value)throw Error('Insufficient simulated StudioNet GEN.');
   localStorage.setItem(pendingKey+':probe','1');localStorage.removeItem(pendingKey+':probe');
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
    localStorage.setItem(pendingKey,JSON.stringify(known));onHash(known);
   };
   const writer=createClient({chain:chains.studionet,account:s.address,provider:guarded as never});
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
