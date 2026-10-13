import {describe,expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {createElement} from 'react';
import ReserveProofPanel from './ReserveProofPanel';

describe('v0.4 reserve proof boundary',()=>{
  it('shows actual release sequence and discloses the untested live loss branch',()=>{
    const page=renderToStaticMarkup(createElement(ReserveProofPanel,{status:'REFUNDED'}));
    expect(page).toContain('Latest onchain read: REFUNDED');
    expect(page).toContain('verification.json');
    expect(page).toContain('StudioNet has not produced a live uncredited external child');
    expect(page).toContain('0x9218b57964ae4eBe9c9756bb48b3454a03Ce707D');
  });
});
