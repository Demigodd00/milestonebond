import {useState,type FormEvent} from 'react';

type StageDraft={title:string;criteria:string;paths:string;hours:string;amount:string};
const initialStages:StageDraft[]=[
 {title:'Core implementation',criteria:'The specified behavior is implemented in the changed source.',paths:'src/core.py',hours:'24',amount:'0.01'},
 {title:'Safety and edge cases',criteria:'Invalid input is rejected while the earlier behavior remains intact.',paths:'src/core.py',hours:'48',amount:'0.02'},
];
const sha256=async(bytes:Uint8Array)=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes as BufferSource))].map(b=>b.toString(16).padStart(2,'0')).join('');
export const amount=(value:string)=>{if(!/^\d+(\.\d{1,18})?$/.test(value))throw Error('Each stage needs a decimal test-GEN amount with at most 18 fractional digits.');const [whole,part='']=value.split('.');const n=BigInt(whole)*10n**18n+BigInt(part.padEnd(18,'0'));if(n<10n**15n||n>10n**18n)throw Error('Each stage must be 0.001–1 test GEN.');return n;};
export const asGEN=(n:bigint)=>`${n/10n**18n}.${String(n%10n**18n).padStart(18,'0').replace(/0+$/,'')||'0'}`;
const lines=(s:string,max:number,label:string)=>{const xs=s.split('\n').map(x=>x.trim()).filter(Boolean);if(xs.length<1||xs.length>max||new Set(xs).size!==xs.length)throw Error(`Use 1–${max} distinct ${label}, one per line.`);return xs;};
const github=async(url:string)=>{const response=await fetch(url,{headers:{Accept:'application/vnd.github+json'}});if(!response.ok)throw Error(`GitHub could not verify ${url.split('/').at(-1)} (HTTP ${response.status}). Check that the repository is public and the identifier is exact.`);return response.json() as Promise<Record<string,unknown>>;};

export default function TermsBuilder({onBuild,address}:{onBuild:(terms:string,deposit:string)=>void;address?:string}){
 const [repo,setRepo]=useState('');const [issue,setIssue]=useState('');const [base,setBase]=useState('');const [author,setAuthor]=useState('');
 const [title,setTitle]=useState('');const [id,setId]=useState('');const [workflow,setWorkflow]=useState('.github/workflows/ci.yml');const [job,setJob]=useState('acceptance');
 const [stages,setStages]=useState<StageDraft[]>(initialStages);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [verified,setVerified]=useState('');
 const update=(index:number,key:keyof StageDraft,value:string)=>setStages(rows=>rows.map((row,i)=>i===index?{...row,[key]:value}:row));
 async function build(e:FormEvent){
  e.preventDefault();setError('');setVerified('');setBusy(true);
  try{
   if(!/^MB-[A-Z0-9-]{3,36}$/.test(id))throw Error('Use a unique project ID such as MB-ORDER-001.');
   if(!/^[A-Za-z0-9_-]+\/[A-Za-z0-9_.-]+$/.test(repo)||repo.endsWith('.git'))throw Error('Use a public owner/repository name.');
   if(!/^[0-9a-f]{40}$/.test(base))throw Error('Enter the full lowercase 40-character base commit SHA.');
   if(!/^0x[0-9a-fA-F]{40}$/.test(author)||/^0x0{40}$/i.test(author)||author.toLowerCase()===address?.toLowerCase())throw Error('Enter a nonzero author wallet different from the sponsor.');
   if(!/^\.github\/workflows\/[A-Za-z0-9_-]+\.ya?ml$/.test(workflow))throw Error('Use an exact workflow path under .github/workflows/.');
   if(title.trim().length<1||title.trim().length>100||job.trim().length<1||job.trim().length>100)throw Error('Project title and required job must be 1–100 characters.');
   const issueNumber=Number(issue);if(!Number.isSafeInteger(issueNumber)||issueNumber<1)throw Error('Enter a positive GitHub issue number.');
   const n=Math.floor(Date.now()/1000);let prior=1;let total=0n;
   const milestones=stages.map(row=>{
    const hours=Number(row.hours);if(!Number.isSafeInteger(hours)||hours<2||hours>2160||hours<=prior)throw Error('Milestone due hours must increase, start after hour 1, and stay within 90 days.');prior=hours;
    const criteria=lines(row.criteria,4,'criteria');if(criteria.some(x=>x.length>700))throw Error('Each criterion must be at most 700 characters.');
    const paths=lines(row.paths,4,'source paths');if(paths.some(p=>p.length>180||!/^[-A-Za-z0-9_./]+$/.test(p)||p.startsWith('.github/')||p.split('/').some(x=>!x||x==='.'||x==='..')))throw Error('Use 1–4 exact existing source paths, not wildcards or workflow files.');
    const value=amount(row.amount);total+=value;
    if(row.title.trim().length<1||row.title.trim().length>100)throw Error('Milestone titles must be 1–100 characters.');
    return {title:row.title.trim(),criteria,allowed_paths:paths,due_at:n+hours*3600,amount:value.toString()};
   });
   const root=`https://api.github.com/repos/${repo}`;
   const [repository,issueRecord,commit,contents,workflows]=await Promise.all([
    github(root),github(`${root}/issues/${issueNumber}`),github(`${root}/git/commits/${base}`),
    github(`${root}/contents/${workflow}?ref=${base}`),github(`${root}/actions/workflows?per_page=100`),
   ]);
   if(repository.private!==false||String(repository.full_name).toLowerCase()!==repo.toLowerCase())throw Error('Repository must be public and canonical.');
   if(issueRecord.number!==issueNumber||'pull_request' in issueRecord||typeof issueRecord.body!=='string')throw Error('The selected issue is not a public issue with a body.');
   const issueBytes=new TextEncoder().encode(issueRecord.body);if(issueBytes.length<1||issueBytes.length>5000)throw Error('Issue body must be 1–5000 UTF-8 bytes.');
   if(commit.sha!==base)throw Error('The base commit could not be verified.');
   if(typeof contents.content!=='string'||contents.encoding!=='base64')throw Error('GitHub did not return pinned workflow bytes.');
   const encoded=contents.content.replace(/\s/g,'');const raw=atob(encoded);const workflowBytes=Uint8Array.from(raw,c=>c.charCodeAt(0));
   if(workflowBytes.length<1||workflowBytes.length>12000)throw Error('Workflow must be 1–12000 bytes.');
   const items=workflows.workflows;if(!Array.isArray(items)||workflows.total_count!==items.length)throw Error('Workflow list is incomplete; use the advanced editor after verifying the workflow ID.');
   const matches=items.filter(x=>x&&typeof x==='object'&&(x as Record<string,unknown>).path===workflow);
   if(matches.length!==1)throw Error('The exact workflow path was not found in the repository’s registered Actions workflows.');
   const workflowId=(matches[0] as Record<string,unknown>).id;if(!Number.isSafeInteger(workflowId)||Number(workflowId)<1)throw Error('Invalid GitHub workflow ID.');
   const terms={id,title:title.trim(),repo,issue_number:issueNumber,issue_sha256:await sha256(issueBytes),base_sha:base,author:author.toLowerCase(),workflow_path:workflow,
    workflow_sha256:await sha256(workflowBytes),workflow_bytes:workflowBytes.length,workflow_id:workflowId,required_job:job.trim(),accept_by:n+3600,milestones};
   onBuild(JSON.stringify(terms,null,2),asGEN(total));
   setVerified(`Fetched issue #${issueNumber}, base ${base.slice(0,10)}…, workflow ${workflowId} (${workflowBytes.length} bytes). Review the generated immutable terms below before signing.`);
   document.getElementById('terms-json')?.scrollIntoView({behavior:'smooth',block:'center'});
  }catch(err){setError(err instanceof Error?err.message:String(err));}finally{setBusy(false);}
 }
 return <form className="terms-builder" onSubmit={build}><div className="panel-title">GUIDED TERMS BUILDER <span>Public GitHub data only</span></div><p>Fill the project and stage terms. We fetch the public issue, base commit and workflow, then calculate their exact SHA-256 commitments for you. Nothing is signed at this step.</p><div className="form-grid"><label>Project ID<input value={id} onChange={e=>setId(e.target.value)} placeholder="MB-ORDER-001" required/></label><label>Project title<input value={title} onChange={e=>setTitle(e.target.value)} maxLength={100} required/></label><label>Public repository<input value={repo} onChange={e=>setRepo(e.target.value.trim())} placeholder="owner/repository" required/></label><label>Issue number<input value={issue} onChange={e=>setIssue(e.target.value)} inputMode="numeric" required/></label><label>Full base commit SHA<input value={base} onChange={e=>setBase(e.target.value.trim())} placeholder="40 lowercase hex characters" required/></label><label>Assigned author wallet<input value={author} onChange={e=>setAuthor(e.target.value.trim())} placeholder="0x…" required/></label><label>Workflow path<input value={workflow} onChange={e=>setWorkflow(e.target.value.trim())} required/></label><label>Exact CI job name<input value={job} onChange={e=>setJob(e.target.value)} required/></label></div><div className="builder-stages"><div className="builder-stages-head"><strong>Funded milestones</strong><button type="button" className="secondary" disabled={stages.length===4} onClick={()=>setStages(rows=>[...rows,{title:'',criteria:'',paths:'',hours:String((Number(rows.at(-1)?.hours)||24)+24),amount:'0.01'}])}>+ Add stage</button></div>{stages.map((row,i)=><div className="builder-stage" key={i}><div className="builder-stage-title"><strong>Stage {i+1}</strong>{stages.length>2&&<button type="button" className="text-action" onClick={()=>setStages(rows=>rows.filter((_,j)=>j!==i))}>Remove</button>}</div><div className="form-grid"><label>Title<input value={row.title} onChange={e=>update(i,'title',e.target.value)} required maxLength={100}/></label><label>Amount · test GEN<input value={row.amount} onChange={e=>update(i,'amount',e.target.value)} required inputMode="decimal"/></label><label>Due hours from creation<input value={row.hours} onChange={e=>update(i,'hours',e.target.value)} required inputMode="numeric"/></label><label>Allowed files · one per line<textarea value={row.paths} onChange={e=>update(i,'paths',e.target.value)} required rows={2}/></label></div><label>Acceptance criteria · one per line<textarea value={row.criteria} onChange={e=>update(i,'criteria',e.target.value)} required rows={3}/></label></div>)}</div>{error&&<div className="builder-error" role="alert">{error}</div>}{verified&&<div className="builder-success" role="status">{verified}</div>}<button className="secondary" disabled={busy}>{busy?'Fetching public GitHub evidence…':'Generate immutable terms'}</button></form>;
}
