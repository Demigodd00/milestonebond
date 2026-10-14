import {readFileSync} from 'node:fs';
import {describe,expect,it} from 'vitest';

const load=(name:string)=>JSON.parse(readFileSync(new URL(`../public/${name}`,import.meta.url),'utf8'));

describe('published Bradbury release',()=>{
 it('points the live app to the independently verified v0.5 deployment',()=>{
  const deployment=load('deployment.json');
  const proof=load('verification-v0.5.json');
  expect(deployment).toMatchObject({verified:true,chainId:4221,network:'bradbury',version:'milestonebond.v0.5'});
  expect(deployment.address).toBe(proof.contract);
  expect(deployment.sourceSha256).toBe(proof.source_sha256);
  expect(proof.source_verified).toBe(true);
 });

 it('publishes a finalized failure and restored, unpaid credit—not a payout claim',()=>{
  const proof=load('verification-v0.5.json');
  expect(proof.transactions.map((tx:{method:string})=>tx.method)).toEqual([
   'create_project','recover_expired','withdraw_to','reconcile_withdrawal']);
  expect(proof.transactions.every((tx:{status:string;execution_success:boolean})=>
   tx.status==='FINALIZED'&&tx.execution_success)).toBe(true);
  expect(proof.failure.failure_event_family).toBe('MessageProcessorFailure');
  expect(proof.failure.receiver_balance_after).toBe(proof.failure.receiver_balance_before);
  expect(proof.failure.contract_balance_after).toBe(proof.failure.contract_balance_before);
  expect(proof.project_accounting.claimable).toBe('2000000000000000');
  expect(proof.accounting.pending_withdrawal).toBeNull();
  expect(proof.accounting.pending_out).toBe('0');
  expect(proof.accounting.withdrawn).toBe('0');
  expect(proof.project_accounting.reserve_consumed).toBe('0');
 });
});
