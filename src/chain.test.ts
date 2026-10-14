import {afterEach,describe,expect,it,vi} from 'vitest';
import {connect,findFinalization,pendingKeyFor,receiptOutcome,verifyDeployment} from './chain';

afterEach(()=>vi.unstubAllGlobals());

describe('browser wallet handshake',()=>{
 it('connects an EIP-1193 wallet already on StudioNet without requesting a signature',async()=>{
  const address='0x1111111111111111111111111111111111111111';
  const request=vi.fn(async({method}:{method:string})=>method==='eth_requestAccounts'?[address]:'0x'+(61999).toString(16));
  vi.stubGlobal('window',{ethereum:{request}});
  const session=await connect();
  expect(session.address).toBe(address);
  expect(request.mock.calls.map(([call])=>call.method)).toEqual(['eth_requestAccounts','eth_chainId']);
 });
 it('asks the wallet to switch to StudioNet when the chain differs',async()=>{
  const address='0x2222222222222222222222222222222222222222';
  const request=vi.fn(async({method}:{method:string})=>method==='eth_requestAccounts'?[address]:method==='eth_chainId'?'0x1':null);
  vi.stubGlobal('window',{ethereum:{request}});
  await connect();
  expect(request.mock.calls.map(([call])=>call.method)).toEqual(['eth_requestAccounts','eth_chainId','wallet_switchEthereumChain']);
  expect(request.mock.calls[2][0]).toEqual({method:'wallet_switchEthereumChain',params:[{chainId:'0x'+(61999).toString(16)}]});
 });
 it('checks Bradbury ghost code even when wallet reports chain ID 4221',async()=>{
  const d={verified:true,address:'0x1111111111111111111111111111111111111111',chainId:4221,sourceSha256:'a'.repeat(64),version:'milestonebond.v0.5',network:'bradbury'};
  const request=vi.fn(async({method}:{method:string})=>method==='eth_requestAccounts'?[d.address]:method==='eth_chainId'?'0x107d':method==='eth_getCode'?'0x6000':null);
  vi.stubGlobal('window',{ethereum:{request}});
  const session=await connect(d);
  expect(session.address).toBe(d.address);
  expect(request.mock.calls.map(([call])=>call.method)).toEqual(['eth_requestAccounts','eth_chainId','eth_getCode']);
  expect(pendingKeyFor(d)).toBe('milestonebond:pending:v0.5:4221');
 });
 it('refuses a 4221 wallet with no Bradbury ghost at the published address',async()=>{
  const d={verified:true,address:'0x1111111111111111111111111111111111111111',chainId:4221,sourceSha256:'a'.repeat(64),version:'milestonebond.v0.5',network:'bradbury'};
  const request=vi.fn(async({method}:{method:string})=>method==='eth_requestAccounts'?[d.address]:method==='eth_chainId'?'0x107d':'0x');
  vi.stubGlobal('window',{ethereum:{request}});
  await expect(connect(d)).rejects.toThrow('not connected to the Bradbury chain');
 });
});

describe('transaction outcome',()=>{
 it('does not mistake acceptance for execution success',()=>{
  expect(receiptOutcome({statusName:'ACCEPTED',consensusData:{leaderReceipt:{executionResult:'SUCCESS'}}})).toBe('pending');
 });
 it('marks a finalized execution error honestly',()=>{
  expect(receiptOutcome({statusName:'FINALIZED',consensusData:{leaderReceipt:{mode:'leader',executionResult:'ERROR'}}})).toBe('error');
 });
 it('accepts only finalized successful execution',()=>{
  expect(receiptOutcome({statusName:'FINALIZED',consensusData:{leaderReceipt:[{mode:'validator',executionResult:'SUCCESS'},{mode:'leader',executionResult:'SUCCESS'}]}})).toBe('success');
 });
 it('reads the snake_case leader results returned by the current StudioNet SDK',()=>{
  expect(receiptOutcome({statusName:'FINALIZED',consensusData:{leaderReceipt:[{mode:'leader',execution_result:'SUCCESS'}]}})).toBe('success');
  expect(receiptOutcome({statusName:'FINALIZED',consensusData:{leaderReceipt:[{mode:'leader',execution_result:'ERROR'}]}})).toBe('error');
 });
 it('treats an unknown finalized receipt as unresolved',()=>{
  expect(receiptOutcome({statusName:'FINALIZED'})).toBe('pending');
 });
 it('uses raw Bradbury status and execution codes, including unrecognized provisional states',()=>{
  expect(receiptOutcome({status:5,txExecutionResult:1})).toBe('pending');
  expect(receiptOutcome({status:14,txExecutionResult:1})).toBe('pending');
  expect(receiptOutcome({status:7,txExecutionResult:1})).toBe('success');
  expect(receiptOutcome({status:7,txExecutionResult:2})).toBe('error');
  expect(receiptOutcome({status:7,txExecutionResult:0})).toBe('pending');
 });
});

describe('Bradbury finalization lookup',()=>{
 it('binds an EVM finalization hash to the exact GenLayer withdrawal ID',async()=>{
  const parent='0x'+'2'.repeat(64),evm='0x'+'3'.repeat(64);
  const topic='0x24196ec40f90671b7144e716978686b4f3c7d6b00b23da3971ef2b52af27d87f';
  const calls:string[]=[];
  vi.stubGlobal('fetch',vi.fn(async(_url:string,options:{body:string})=>{const req=JSON.parse(options.body);calls.push(req.method);return {ok:true,json:async()=>({result:req.method==='eth_blockNumber'?'0x2710':[{address:'0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D',topics:[topic,parent],transactionHash:evm}]})};}));
  await expect(findFinalization(parent)).resolves.toBe(evm);
  expect(calls).toEqual(['eth_blockNumber','eth_getLogs']);
 });
 it('keeps a missing finalization unresolved',async()=>{
  const parent='0x'+'2'.repeat(64);
  vi.stubGlobal('fetch',vi.fn(async(_url:string,options:{body:string})=>{const req=JSON.parse(options.body);return {ok:true,json:async()=>({result:req.method==='eth_blockNumber'?'0x2710':[]})};}));
  await expect(findFinalization(parent)).resolves.toBeNull();
 });
});

describe('release policy guard',()=>{
 it('will not sign against the historical v0.2 address',async()=>{
  await expect(verifyDeployment({verified:true,address:'0xb437593b7656254226ce496bc6f9A052A11D6345',chainId:61999,sourceSha256:'1'.repeat(64),version:'milestonebond.v0.2',network:'studionet'})).rejects.toThrow('Live signing is disabled');
 });
});
