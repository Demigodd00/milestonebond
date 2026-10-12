import {describe,expect,it} from 'vitest';
import {receiptOutcome} from './chain';

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
 it('treats an unknown finalized receipt as unresolved',()=>{
  expect(receiptOutcome({statusName:'FINALIZED'})).toBe('pending');
 });
});
