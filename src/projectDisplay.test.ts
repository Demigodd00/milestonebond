import {describe,expect,it} from 'vitest';
import {baseLabels} from './projectDisplay';

describe('project base labels',()=>{
  it('shows the frozen base before any review',()=>{
    expect(baseLabels({base_sha:'initial',milestones:[{reviews:[]}]})).toEqual({initial:'initial',current:'initial',advanced:false});
  });
  it('keeps the original base visible after later stages advance the head',()=>{
    expect(baseLabels({base_sha:'stage-two',milestones:[{reviews:[{evidence:{base_sha:'initial'}}]}]})).toEqual({initial:'initial',current:'stage-two',advanced:true});
  });
});
