import {describe,expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {createElement} from 'react';
import App,{explorerHref} from './App';

describe('reviewer-facing overview',()=>{
  it('separates the illustrative roadmap from the public live proof',()=>{
    const page=renderToStaticMarkup(createElement(App));
    expect(page).toContain('ILLUSTRATIVE ROADMAP');
    expect(page).toContain('Illustrative three-stage example—not the live onchain project.');
    expect(page).toContain('VERIFIED V0.3 RUN');
    expect(page).toContain('sponsor approve this exact unmerged commit');
    expect(page).toContain('verification.json');
    expect(page).toContain('https://github.com/Demigodd00/milestonebond');
  });
});

describe('explorer links',()=>{
 it('uses live Bradbury routes while preserving StudioNet URLs',()=>{
  expect(explorerHref('https://explorer-bradbury.genlayer.com/transactions/0x123'))
   .toBe('https://explorer-bradbury.genlayer.com/tx/0x123');
  expect(explorerHref('https://explorer-bradbury.genlayer.com/contracts/0xabc'))
   .toBe('https://explorer-bradbury.genlayer.com/address/0xabc');
  expect(explorerHref('https://explorer-studio.genlayer.com/transactions/0x123'))
   .toBe('https://explorer-studio.genlayer.com/transactions/0x123');
 });
});
