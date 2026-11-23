import { FormEvent, useEffect, useState } from "react";
type Finding={title:string;severity:string;file:string;line:number|null;description:string;recommendation:string};
type Report={report_id:string;repository_name:string;repository_url:string;summary:string;findings:Finding[];strengths:string[];limitations:string[]};
type Phase={number:number;name:string;status:string;evidence:string[]};
type QpbRun={run_id:string;repository_name:string;status:string;skill:{installed:boolean;version:string|null;message:string;missing_files:string[]};phases:Phase[];message:string;runtime_capabilities:Record<string,string>};
const API="http://127.0.0.1:8000";
export default function App(){
 const [url,setUrl]=useState(""); const [report,setReport]=useState<Report|null>(null);
 const [error,setError]=useState(""); const [loading,setLoading]=useState(false);
 const [skillStatus,setSkillStatus]=useState<{installed:boolean;version:string|null;message:string}|null>(null);
 const [qpbRun,setQpbRun]=useState<QpbRun|null>(null); const [preparing,setPreparing]=useState(false);
 useEffect(()=>{fetch(`${API}/api/qpb/skill`).then(r=>r.json()).then(setSkillStatus).catch(()=>setSkillStatus(null));},[]);
 async function submit(e:FormEvent){e.preventDefault();setLoading(true);setError("");setReport(null);try{const r=await fetch(`${API}/api/analyze`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({repository_url:url})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Analysis failed");setReport(d);}catch(x){setError(x instanceof Error?x.message:"Backend unavailable");}finally{setLoading(false);}}
 async function prepareQpb(){setPreparing(true);setError("");setQpbRun(null);try{const r=await fetch(`${API}/api/qpb/prepare`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({repository_url:url})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"QPB skill installation failed");setQpbRun(d);}catch(x){setError(x instanceof Error?x.message:"QPB preparation failed");}finally{setPreparing(false);}}
 const counts=report?.findings.reduce<Record<string,number>>((a,f)=>(a[f.severity]=(a[f.severity]||0)+1,a),{})||{};
 return <main className="shell"><header><div className="logo">Q</div><div><b>QualityCheckAgent</b><small>Quality Playbook integration · v1.6.1</small></div></header>
 <section className="hero"><label>QUALITY ENGINEERING WORKFLOW</label><h1>From code review to<br/><em>quality engineering.</em></h1><p>Prepare a repository with the official Quality Playbook skill, then run its six-phase quality workflow with verifiable checkpoints.</p>
 <form onSubmit={submit}><input type="url" required value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://github.com/owner/repository"/><button disabled={loading||preparing}>{loading?"Analyzing…":"Static review"}</button></form>
 <div className="qpb-prepare"><button disabled={!url||preparing||loading} onClick={prepareQpb}>{preparing?"Installing skill…":"Install QPB skill in repository"}</button><small>{skillStatus?skillStatus.message:"Checking pinned QPB skill…"}</small></div>
 <small className="hint">Static review is separate from the official QPB workflow. Installation does not claim that phases have run.</small>
 {(loading||preparing)&&<div className="loading">{loading?"Cloning repository and requesting analysis from Groq…":"Cloning repository and installing official QPB v1.6.1 assets…"}</div>}{error&&<div className="error">{error}</div>}</section>
 {qpbRun&&<section className="results"><div className="resultHead"><div><label>SKILL INSTALLED</label><h2>{qpbRun.repository_name}</h2><p className="muted">QPB v1.6.1 · Run {qpbRun.run_id}</p></div><span className="status-pill">{qpbRun.status}</span></div>
 <div className="summary"><b>{qpbRun.skill.message}</b><p>The official skill files were installed into the target repository. No phase has been executed yet.</p></div>
 <h3>Six-phase workflow</h3><div className="phase-list">{qpbRun.phases.map(p=><div className="phase" key={p.number}><span className="phase-num">{p.number}</span><div><b>{p.name}</b><small>{p.status}</small></div><span className="phase-state">{p.status}</span></div>)}</div>
 <div className="summary"><b>Runtime capability checks</b>{Object.entries(qpbRun.runtime_capabilities).map(([k,v])=><p key={k}>{k.replaceAll("_"," ")}: <code>{v}</code></p>)}</div>
 <p className="disclaimer">{qpbRun.message}</p></section>}
 {report&&<section className="results"><div className="resultHead"><div><label>STATIC REVIEW COMPLETE</label><h2>{report.repository_name}</h2><a href={report.repository_url} target="_blank" rel="noreferrer">{report.repository_url}</a></div><div className="downloads"><a className="download" href={`${API}/api/reports/${report.report_id}/markdown`}>Download Markdown ↓</a><a className="download secondary" href={`${API}/api/reports/${report.report_id}/docx`}>Download Word ↓</a></div></div>
 <div className="summary"><b>Summary</b><p>{report.summary}</p></div><div className="stats">{["critical","high","medium","low","info"].map(s=><div key={s}><strong>{counts[s]||0}</strong><small>{s}</small></div>)}</div>
 <h3>Findings ({report.findings.length})</h3>{report.findings.length===0?<p className="muted">No concrete findings returned. This does not prove the repository is defect-free.</p>:report.findings.map((f,i)=><article key={i}><div className="findingTitle"><span className={`sev ${f.severity}`}>{f.severity}</span><b>{f.title}</b></div><code>{f.file}{f.line?`:${f.line}`:""}</code><p>{f.description}</p><div className="recommend"><b>Recommendation</b><p>{f.recommendation}</p></div></article>)}
 <div className="columns"><div className="summary"><h3>Strengths</h3>{report.strengths.map((x,i)=><p key={i}>✓ {x}</p>)}</div><div className="summary"><h3>Limitations</h3>{report.limitations.map((x,i)=><p key={i}>• {x}</p>)}</div></div>
 <p className="disclaimer">AI-assisted static review only. Repository code/tests were not executed and official QPB verification gates were not run.</p></section>}<footer>QualityCheckAgent · QPB v1.6.1 integration</footer></main>;
}
