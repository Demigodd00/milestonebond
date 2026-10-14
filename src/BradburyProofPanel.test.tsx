import {describe,expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import BradburyProofPanel from './BradburyProofPanel';

describe('Bradbury proof panel',()=>{
 it('does not assert recovery before the finalized record loads',()=>{
  const markup=renderToStaticMarkup(<BradburyProofPanel/>);
  expect(markup).toContain('V0.5 BRADBURY FAILURE RUN');
  expect(markup).toContain('Loading the independently checked Bradbury evidence record');
  expect(markup).not.toContain('Entitlement restored once');
 });
});
