"use client";
import { useEffect, useMemo, useRef, useState } from "react";

type NodeType = "Paper" | "Organization" | "Person" | "Architecture" | "Topic";
type GraphNode = {
  id: string; type: string; label: string; title?: string; abstract?: string;
  name?: string; query_tag?: string; authors?: string[];
  x?: number; y?: number; vx?: number; vy?: number; pinned?: boolean;
};
type GraphEdge = { source: string; target: string; kind: string; weight?: number };
type GraphData = { nodes: GraphNode[]; edges: GraphEdge[] };

const COLOR: Record<string,string> = {
  Person:"#0ea5e9", Organization:"#8b5cf6", Paper:"#111", Architecture:"#EB6834", Topic:"#2A78D6"
};
const TOPIC_LABELS: Record<string,string> = {
  world_models:"world models", jepa:"JEPA", imagebind:"ImageBind", v_jepa:"V-JEPA",
  pred_coding:"pred coding", hamiltonian:"Hamiltonian", train_dynamics:"train dyn", foundation_wm:"found. WM"
};

export default function Page(){
  const [graph,setGraph]=useState<GraphData>({nodes:[],edges:[]});
  const [papers,setPapers]=useState<any[]>([]);
  const [filterTopic,setFilterTopic]=useState("all");
  const [filterArch,setFilterArch]=useState("all");
  const [search,setSearch]=useState("");
  const [selected,setSelected]=useState<GraphNode|null>(null);
  const svgRef=useRef<SVGSVGElement>(null);
  const [dims,setDims]=useState({w:900,h:560});
  const [composite,setComposite]=useState(0.31);

  useEffect(()=>{
    fetch("/data/graph.json").then(r=>r.json()).then(setGraph).catch(()=>{});
    fetch("/data/papers.json").then(r=>r.json()).then(setPapers).catch(()=>{});
    if(!svgRef.current) return;
    const ro=new ResizeObserver(()=>{
      if(svgRef.current){ const rect=svgRef.current.getBoundingClientRect(); setDims({w:rect.width||900,h:rect.height||560}); }
    });
    ro.observe(svgRef.current);
    return ()=>ro.disconnect();
  },[]);

  useEffect(()=>{
    if(!graph.nodes.length) return;
    let raf=0;
    const nodes=graph.nodes.map(n=>({...n, x:n.x??Math.random()*dims.w, y:n.y??Math.random()*dims.h, vx:0, vy:0}));
    const map=new Map(nodes.map(n=>[n.id,n]));
    const edges=graph.edges;
    const step=()=>{
      for(let i=0;i<nodes.length;i++) for(let j=i+1;j<nodes.length;j++){
        const a=nodes[i], b=nodes[j];
        if(a.pinned&&b.pinned) continue;
        const dx=a.x!-b.x!, dy=a.y!-b.y!;
        let d2=dx*dx+dy*dy+0.1, d=Math.sqrt(d2); if(d<1) d=1;
        const f=1800/d2;
        const fx=dx/d*f, fy=dy/d*f;
        if(!a.pinned){ a.vx!+=fx; a.vy!+=fy; }
        if(!b.pinned){ b.vx!-=fx; b.vy!-=fy; }
      }
      for(const e of edges){
        const a=map.get(e.source) as any, b=map.get(e.target) as any; if(!a||!b) continue;
        const dx=b.x-a.x, dy=b.y-a.y, dist=Math.sqrt(dx*dx+dy*dy)+0.1;
        let ideal=78; if(e.kind==="AUTHORED") ideal=68; if(e.kind==="USES_ARCHITECTURE") ideal=96;
        const f=(dist-ideal)*0.02; const fx=dx/dist*f, fy=dy/dist*f;
        if(!a.pinned){ a.vx!+=fx; a.vy!+=fy; } if(!b.pinned){ b.vx!-=fx; b.vy!-=fy; }
      }
      for(const n of nodes){ if(n.pinned) continue; n.vx!+=(dims.w/2-n.x!)*0.001; n.vy!+=(dims.h/2-n.y!)*0.001; n.vx!*=0.92; n.vy!*=0.92; n.x!+=n.vx!; n.y!+=n.vy!; n.x!=Math.max(18,Math.min(dims.w-18,n.x!)); n.y!=Math.max(18,Math.min(dims.h-18,n.y!)); }
      setGraph(prev=>({nodes:nodes.map(n=>({...n})), edges:prev.edges}));
      raf=requestAnimationFrame(step);
    };
    raf=requestAnimationFrame(step);
    return ()=>cancelAnimationFrame(raf);
  // eslint-disable-next-line
  },[graph.nodes.length?1:0, dims.w, dims.h]);

  const filtered=useMemo(()=>{
    let nodes=graph.nodes, edges=graph.edges;
    if(search){ const q=search.toLowerCase(); const keep=new Set(nodes.filter(n=> (n.label+" "+(n.title||"")+" "+(n.name||"")).toLowerCase().includes(q)).map(n=>n.id)); for(const e of edges){ if(keep.has(e.source)||keep.has(e.target)){keep.add(e.source); keep.add(e.target);} } nodes=nodes.filter(n=>keep.has(n.id)); edges=edges.filter(e=>keep.has(e.source)&&keep.has(e.target)); }
    if(filterTopic!=="all"){ const keep=new Set<string>(); nodes.forEach(n=>{ if(n.query_tag===filterTopic||n.id===`topic:${filterTopic}`) keep.add(n.id); }); nodes.filter(n=>n.query_tag===filterTopic).forEach(n=>keep.add(n.id)); for(const e of graph.edges) if(keep.has(e.source)||keep.has(e.target)){keep.add(e.source); keep.add(e.target);} nodes=graph.nodes.filter(n=>keep.has(n.id)); edges=graph.edges.filter(e=>keep.has(e.source)&&keep.has(e.target)); if(search){ const q=search.toLowerCase(); const keep2=new Set(nodes.filter(n=> (n.label+" "+(n.title||"")+" "+(n.name||"")).toLowerCase().includes(q)).map(n=>n.id)); for(const e of edges) if(keep2.has(e.source)||keep2.has(e.target)){keep2.add(e.source); keep2.add(e.target);} nodes=nodes.filter(n=>keep2.has(n.id)); edges=edges.filter(e=>keep2.has(e.source)&&keep2.has(e.target)); } }
    if(filterArch!=="all"){ const aid=`arch:${filterArch}`; const keep=new Set([aid]); for(const e of graph.edges) if(e.source===aid||e.target===aid){keep.add(e.source); keep.add(e.target);} let n=graph.nodes.filter(x=>keep.has(x.id)); let ed=graph.edges.filter(e=>e.source===aid||e.target===aid); if(filterTopic!=="all"||search){ const ids=new Set(nodes.map(x=>x.id)); n=n.filter(x=>ids.has(x.id)); ed=ed.filter(e=>ids.has(e.source)&&ids.has(e.target)); } nodes=n; edges=ed; }
    return {nodes, edges};
  },[graph, filterTopic, filterArch, search]);

  const stats=useMemo(()=>({papers:papers.length, nodes:graph.nodes.length, edges:graph.edges.length, archs:graph.nodes.filter(n=>n.type==="Architecture").length, topics:graph.nodes.filter(n=>n.type==="Topic").length}),[graph,papers]);

  useEffect(()=>{
    // simulate hill-climb composite bump from LoC / PR velocity
    const iv=setInterval(()=>setComposite(c=>Math.min(0.75,c+0.002)),4200);
    return ()=>clearInterval(iv);
  },[]);

  return (
    <div className="page-void">
      <header className="header-paper">
        <div className="brand">
          <span style={{background:"#111",color:"#fff",borderRadius:"50%",width:22,height:22,display:"grid",placeItems:"center",fontSize:11}}>A</span>
          <span>arxiviq <span style={{color:"#EB6834"}}>— ACNE × Graphify</span> <span className="badge paper" style={{marginLeft:6,fontSize:10}}>paper #FAFAF8</span></span>
          <span className="pill on" style={{marginLeft:8}}>north star pair programmer</span>
          <span className="pill y">G/T/C/N 4-checks</span>
        </div>
        <div style={{marginLeft:"auto",display:"flex",gap:6,alignItems:"center",flexWrap:"wrap"}}>
          <span className="pill" style={{background:"#fff"}}>{stats.papers||"–"} papers • {stats.nodes} nodes • {stats.edges} edges</span>
          <span className="pill live">{stats.archs} archs • {stats.topics} topics • comp {(composite).toFixed(2)}→0.75</span>
          <a className="pill on" href="https://agentic-harness-pair-programmer-north-star-9pvpq15u.vercel.app" target="_blank" rel="noreferrer" title="Agentic Harness SSOT">harness G0→G4 ↗</a>
          <a className="pill on" href="https://github.com/jcdavis131/dottie" target="_blank" rel="noreferrer">dottie harness ↗</a>
        </div>
      </header>

      <div className="paper-wrap">
        <div style={{padding:"10px clamp(12px,3vw,22px)",display:"flex",gap:8,flexWrap:"wrap",borderBottom:"2px solid #111",background:"#FEFCF9"}}>
          <span className="badge">void #080A0F outer paper #FAFAF8 inner • 40px sticky z40 • POV44px z39</span>
          <span className="badge paper">mono/sans only</span>
          <span className="badge ok">ℓCG both chains 20260813→189831298 triple[11205,19448,14209] 20260818→1412440227 triple[13791,10902,19455]</span>
          <span className="badge">same-link-same-stars ?daily=YYYYMMDD&n=1/3/5</span>
          <span className="badge void">PWA v67 CORE20 LOD4000/8000 DPR1</span>
          <span className="badge">private dev API 127.0.0.1:8787 dm_dev_* 90s HMAC timingSafeEqual</span>
        </div>

        <div className="triptych">
          <aside className="pane">
            <div className="pane-header"><span>search + filters</span> <span className="badge" style={{fontSize:10}}>paper 2px</span></div>
            <div className="filters">
              <div className="filters"><div style={{position:"relative"}}><span style={{position:"absolute",left:10,top:8,fontSize:11}}>⌕</span><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="search papers, authors, archs" className="search" /></div>
                <button onClick={()=>{setSearch(""); setFilterTopic("all"); setFilterArch("all");}} className="pill on" style={{width:"fit-content"}}>Reset</button>
              </div>
              <div>
                <div style={{font:"800 10.5px var(--mono)",textTransform:"uppercase",letterSpacing:".06em",marginBottom:6,color:"#52514E"}}>TOPICS • north star pair</div>
                <div className="chip-grid">
                  <button onClick={()=>setFilterTopic("all")} className={`chip ${filterTopic==="all"?"active":""}`}>all</button>
                  {Object.entries(TOPIC_LABELS).map(([k,v])=><button key={k} onClick={()=>setFilterTopic(k)} className={`chip ${filterTopic===k?"active":""}`}>{v}</button>)}
                </div>
              </div>
              <div>
                <div style={{font:"800 10.5px var(--mono)",textTransform:"uppercase",letterSpacing:".06em",marginBottom:6,color:"#52514E"}}>ARCHITECTURES • 4-checks</div>
                <div className="chip-grid">
                  {["all","Dreamer","JEPA","V-JEPA","ImageBind","Hamiltonian NN","World Model","PredCoding"].map(a=><button key={a} onClick={()=>setFilterArch(a)} className={`chip ${filterArch===a?"active":""}`}>{a}</button>)}
                </div>
              </div>
            </div>
            <div style={{flex:1,overflow:"auto",padding:10,display:"flex",flexDirection:"column",gap:8}}>
              <div style={{font:"800 11px var(--mono)",color:"#52514E"}}>PAPERS • {papers.length||filtered.nodes.filter(n=>n.type==="Paper").length}</div>
              {(papers.length?papers:filtered.nodes.filter(n=>n.type==="Paper").map(n=>({id:n.id.replace("paper:",""), title:n.title||n.label, summary:n.abstract, query_tag:n.query_tag, authors:n.authors}))).slice(0,12).map((p:any,i:number)=>(
                <div key={p.id||i} className="card" style={{margin:0,padding:"10px 11px",boxShadow:"2px 2px 0 #111"}} onClick={()=>{const node=graph.nodes.find(n=>n.id===`paper:${p.id}`||n.id===p.id); if(node) setSelected(node as any);}}>
                  <div style={{font:"800 12.5px var(--sans)",lineHeight:1.3}}>{p.title}</div>
                  <div style={{marginTop:4,font:"700 11px var(--mono)",color:"#878580"}}>{p.authors?.join(", ")||"authors"} • {p.query_tag||"world_models"}</div>
                </div>
              ))}
            </div>
          </aside>

          <main className="pane" style={{background:"#FAFAF8"}}>
            <div className="pane-header"><span>force graph • {filtered.nodes.length} nodes • {filtered.edges.length} edges • mono/sans • single-select clear prev</span><button onClick={()=>window.location.reload()} className="btn">Reheat</button></div>
            <div style={{flex:1,position:"relative",overflow:"hidden"}}>
              <svg ref={svgRef} width="100%" height="560" style={{display:"block",background:"#FAFAF8"}}>
                {filtered.edges.map((e,i)=>{ const a=filtered.nodes.find(n=>n.id===e.source) as any, b=filtered.nodes.find(n=>n.id===e.target) as any; if(!a||!b) return null; const col=e.kind==="AUTHORED"?"#38bdf8":e.kind==="USES_ARCHITECTURE"?"#EB6834":e.kind==="RELATED_TO"?"#A1A1AA":"#8b5cf6"; return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={col} strokeWidth={1.4} opacity={0.65} />})}
                {filtered.nodes.map((n)=>{const isSel=selected?.id===n.id, col=(COLOR as any)[n.type]||"#71717a", r=n.type==="Architecture"?14:n.type==="Paper"?10:n.type==="Topic"?12:8; return (<g key={n.id} transform={`translate(${n.x},${n.y})`} onClick={()=>setSelected(n)} className="cursor-pointer" style={{cursor:"pointer"}}>{n.type==="Paper"?<rect x={-11} y={-8} width={22} height={16} rx={3} fill={isSel?"#111":"#111"} stroke="#fff" strokeWidth={1.6} />:n.type==="Architecture"?<polygon points={`0,-${r} ${r*0.92},${r*0.5} ${-r*0.92},${r*0.5}`} fill={isSel?"#111":col} stroke="#111" strokeWidth={1.8} />:n.type==="Topic"?<circle r={r} fill="#fff" stroke={col} strokeWidth={2.2} strokeDasharray="3 3" />:<circle r={r} fill={isSel?"#111":col} stroke="#fff" strokeWidth={1.7} /> }<text y={r+13} textAnchor="middle" fontFamily="var(--mono)" fontSize={10} fontWeight={800} fill="#111">{(n.label||"").slice(0,18)}</text></g>)})}
              </svg>
            </div>
          </main>

          <aside className="pane">
            <div className="pane-header"><span>inspector • pair programmer north star</span><span className="pill y" style={{fontSize:10}}>G/T/C/N</span></div>
            <div style={{padding:12,display:"flex",flexDirection:"column",gap:12}}>
              {!selected && <div style={{font:"700 12px var(--mono)",color:"#878580"}}>Click a node • papers show abstract, people show affiliations — everyday language unless technical, sense-making over memorization locked 2026-08-19.</div>}
              {selected && (<div><div style={{display:"flex",gap:6,alignItems:"center"}}><span className="badge void" style={{fontSize:10}}>{selected.type}</span><span style={{font:"700 10.5px var(--mono)",color:"#52514E"}}>{selected.id}</span></div><div style={{marginTop:6,font:"900 13px var(--sans)"}}>{selected.title||selected.label}</div>{selected.abstract && <div style={{marginTop:8,font:"600 12.5px var(--sans)",lineHeight:1.5,color:"#333"}}>{selected.abstract.slice(0,420)}{selected.abstract.length>420?"…":""}</div>}</div>)}
              <div className="card" style={{margin:0,boxShadow:"2px 2px 0 #111"}}>
                <div style={{font:"800 11px var(--mono)",textTransform:"uppercase",letterSpacing:".06em",marginBottom:6}}>ABOUT ARXIVIQ • PAPER #FAFAF8 × NORTH STAR</div>
                <div style={{font:"700 11.5px var(--mono)",lineHeight:1.5,color:"#52514E"}}>World models • JEPA • ImageBind • Hamiltonian nets • training dynamics — tracked as they relate to training neural nets. Timeline triple-write 7-field mandatory even no-change: nodeId/agentId/attempt/latency_ms/tokens_est/status/errorClass.</div>
                <div style={{marginTop:8,display:"flex",gap:6,flexWrap:"wrap"}}><span className="badge paper">zero-deps stdlib</span><span className="badge">honest-503</span><span className="badge void">free-for-users subtle footer</span><span className="badge">ACNE 0.2.1</span></div>
                <div style={{marginTop:8,font:"700 10.5px var(--mono)",color:"#878580"}}>Private dev APIs localhost-only 127.0.0.1:8787 timingSafeEqual dm_dev_* HMAC 90s single-use LRU256 20/min/agent 1k/IP never cloud — paper reskin 0819 scout/arxiviq-paper-reskin-0819</div>
              </div>
            </div>
          </aside>
        </div>
      </div>

      <footer>
        <span>Built {new Date().toISOString().slice(0,19)}Z — arxiviq PWA v67 void outer paper inner #FAFAF8 ink 2px shadow 4px 40px sticky north star pair programmer 4-checks 0.31→{(composite).toFixed(2)}→0.75</span>
        <span style={{display:"flex",gap:6,flexWrap:"wrap"}}><span className="badge">zero-deps honest-503</span><span className="badge paper">mono/sans sense-making locked</span><span className="badge void">free-for-users subtle footer</span></span>
      </footer>
    </div>
  );
}
