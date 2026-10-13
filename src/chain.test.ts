import {afterEach,describe,expect,it,vi} from 'vitest';
import {connect,receiptOutcome,verifyDeployment} from './chain';

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
});

describe('release policy guard',()=>{
 it('will not sign against the historical v0.2 address',async()=>{
  await expect(verifyDeployment({verified:true,address:'0xb437593b7656254226ce496bc6f9A052A11D6345',chainId:61999,sourceSha256:'1'.repeat(64),version:'milestonebond.v0.2',network:'studionet'})).rejects.toThrow('Live signing is disabled');
 });
});
