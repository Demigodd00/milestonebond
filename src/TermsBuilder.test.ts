import {describe,expect,it} from 'vitest';
import {amount,asGEN} from './TermsBuilder';

describe('sponsor amounts',()=>{
 it('preserves exact atto-GEN rather than floating-point rounding',()=>{
  expect(amount('0.001000000000000001')).toBe(1000000000000001n);
  expect(asGEN(amount('0.001000000000000001'))).toBe('0.001000000000000001');
 });
 it('rejects out-of-range and overprecision amounts',()=>{
  expect(()=>amount('0.0009')).toThrow();
  expect(()=>amount('1.000000000000000001')).toThrow();
  expect(()=>amount('0.1234567890123456789')).toThrow();
 });
});
