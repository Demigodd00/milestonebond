import {describe,expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {createElement} from 'react';
import App from './App';

describe('reviewer-facing overview',()=>{
  it('separates the illustrative roadmap from the public live proof',()=>{
    const page=renderToStaticMarkup(createElement(App));
    expect(page).toContain('ILLUSTRATIVE ROADMAP');
    expect(page).toContain('Illustrative three-stage example—not the live onchain project.');
    expect(page).toContain('VERIFY THE LIVE RUN');
    expect(page).toContain('sponsor approve this exact unmerged commit');
    expect(page).toContain('verification.json');
    expect(page).toContain('https://github.com/Demigodd00/milestonebond');
  });
});
