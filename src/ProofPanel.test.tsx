import {describe,expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {createElement} from 'react';
import ProofPanel from './ProofPanel';

describe('published proof and live-state boundary',()=>{
  it('labels an absent live project as archival evidence only',()=>{
    const page=renderToStaticMarkup(createElement(ProofPanel,{readReady:true}));
    expect(page).toContain('No current onchain demo; archived record only');
    expect(page).toContain('StudioNet may reset');
  });
  it('shows the v0.3 negative and payout receipts while retaining the v0.2 archive',()=>{
    const page=renderToStaticMarkup(createElement(ProofPanel,{liveStatus:'COMPLETE',readReady:true}));
    expect(page).toContain('Latest onchain read: COMPLETE');
    expect(page).toContain('Stage 2 receipt');
    expect(page).toContain('Transfer receipt');
    expect(page).toContain('Premature review rejected');
    expect(page).toContain('Wrong parent rejected');
    expect(page).toContain('verification-v0.2.json');
  });
});
