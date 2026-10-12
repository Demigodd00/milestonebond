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
  it('shows a loaded contract status without hiding the historical receipt links',()=>{
    const page=renderToStaticMarkup(createElement(ProofPanel,{liveStatus:'COMPLETE',readReady:true}));
    expect(page).toContain('Latest onchain read: COMPLETE');
    expect(page).toContain('Stage 2 receipt');
    expect(page).toContain('Transfer receipt');
  });
});
