import { useState, useRef, useEffect } from "react";

const API_BASE = "https://ananyadixit12-shl-recommendation-api.hf.space";

const T = {
  bg:"#F5F5DC",bgCard:"#FEFCF4",bgCardHover:"#FDF8EC",bgPanel:"#EDE8D5",bgInput:"#FAF8EF",
  border:"#D8D0BC",borderHover:"#BCA898",orange:"#C0784A",orangeHover:"#A8633C",
  orangeLight:"#D4936A",orangeGlow:"#C0784A16",orangeDim:"#C0784A0E",
  green:"#6B8C5A",text1:"#2C1A0E",text2:"#5A3E2B",text3:"#8A6E58",text4:"#B09880",text5:"#D8CEC4",
  scoreHigh:"#5A7E48",scoreMed:"#B87830",scoreLow:"#B04840",
  tagIT:"#4A7AA8",tagBiz:"#785EA8",tagSales:"#C07048",tagHealth:"#488A6A",tagDefault:"#8A7060",
};

const familyColor = f => ({
  "Information Technology":T.tagIT,"Business":T.tagBiz,"Sales":T.tagSales,
  "Healthcare":T.tagHealth,"Contact Center":"#A07850","Clerical":"#788060",
}[f] || T.tagDefault);

const scoreColor = p => p>=70?T.scoreHigh:p>=45?T.scoreMed:T.scoreLow;

const parseTT = tt => {
  if(!tt) return [];
  if(Array.isArray(tt)) return tt.filter(Boolean);
  return tt.split("|").map(s=>s.trim()).filter(Boolean);
};

const JOB_LEVELS=["Entry-Level","Graduate","Mid-Professional","Professional Individual Contributor",
  "Manager","Supervisor","Front Line Manager","Director","Executive","General Population"];

const ROLE_QUERY_MAP = [
  ["content writer",  "english comprehension written english search engine optimization drupal OPQ personality verbal"],
  ["seo",             "search engine optimization english comprehension written english verbal"],
  ["writer",          "english comprehension written english verbal ability OPQ personality"],
  ["marketing manager","marketing digital advertising inductive reasoning OPQ personality writex email manager"],
  ["marketing",       "marketing digital advertising inductive reasoning verbal english comprehension OPQ"],
  ["coo",             "executive leadership OPQ personality cultural fit enterprise leadership report global skills opq leadership"],
  ["ceo",             "executive leadership OPQ personality enterprise leadership report"],
  ["chief",           "executive leadership OPQ personality enterprise leadership report"],
  ["consultant",      "verify verbal ability numerical calculation OPQ personality professional solution administrative"],
  ["sound-scape",     "verbal ability inductive reasoning marketing english comprehension interpersonal communications"],
  ["sound",           "verbal ability inductive reasoning marketing english comprehension personality"],
  ["product manager", "manager agile SDLC jira confluence OPQ personality competencies project management"],
  ["manager",         "manager OPQ personality competencies leadership management"],
  ["sales",           "sales entry level sales solution personality OPQ communication english comprehension spoken svar"],
  ["data analyst",    "SQL python excel tableau data warehousing SSAS automata sql microsoft excel 365"],
  ["data science",    "python SQL data science automata machine learning"],
  ["analyst",         "numerical verbal ability OPQ personality SQL excel python tableau"],
  ["icici",           "bank administrative assistant numerical verify financial professional clerical data entry"],
  ["admin",           "administrative professional numerical verbal clerical data entry computer"],
  ["customer support","english comprehension spoken english svar verbal ability personality OPQ communication"],
  ["customer service","english comprehension spoken english svar verbal ability personality OPQ"],
  ["java",            "java core java java 8 automata fix personality interpersonal"],
  ["python",          "python SQL javascript automata data science personality"],
];

function smartRewrite(query) {
  const q = query.trim();
  const qLower = q.toLowerCase();
  let qShort = q;
  if(q.length > 400) {
    const lines = q.split('\n').map(l=>l.trim()).filter(Boolean);
    const skillKw = ['python','java','sql','experience','skills','require','proficien',
                     'knowledge','responsib','looking for','expert','must have','qualif','duties'];
    const important = lines.slice(0,4);
    for(const line of lines.slice(4)) {
      if(skillKw.some(k=>line.toLowerCase().includes(k))) important.push(line);
      if(important.length >= 12) break;
    }
    qShort = important.join(' ').slice(0,1200);
  }
  const injections = [], seen = new Set();
  for(const [pattern, expansion] of ROLE_QUERY_MAP) {
    if(new RegExp(pattern).test(qLower) && !seen.has(expansion)) {
      injections.push(expansion);
      seen.add(expansion);
      if(injections.length >= 2) break;
    }
  }
  return injections.length ? qShort + " " + injections.join(" ") : qShort;
}

function SHLLogo({size=48}){
  return(
    <svg width={size*2.8} height={size} viewBox="0 0 140 50" fill="none">
      <path d="M8 36 C8 40 12 43 18 43 C24 43 28 40 28 35 C28 30 24 28 18 26 C12 24 8 22 8 17 C8 12 12 8 18 8 C24 8 28 12 28 16" stroke={T.orange} strokeWidth="4.5" strokeLinecap="round" fill="none"/>
      <path d="M36 8 L36 43 M36 26 L54 26 M54 8 L54 43" stroke={T.orange} strokeWidth="4.5" strokeLinecap="round"/>
      <path d="M62 8 L62 43 L80 43" stroke={T.orange} strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="90" cy="43" r="5" fill={T.green}/>
    </svg>
  );
}

function Tag({children,color=T.tagDefault,dot}){
  return(
    <span style={{display:"inline-flex",alignItems:"center",gap:5,padding:"3px 9px",borderRadius:4,
      fontSize:11,fontWeight:500,background:`${color}14`,color,border:`1px solid ${color}2E`,
      fontFamily:"'DM Mono',monospace",letterSpacing:"0.02em",whiteSpace:"nowrap"}}>
      {dot&&<span style={{width:5,height:5,borderRadius:"50%",background:color,flexShrink:0}}/>}
      {children}
    </span>
  );
}

function ScoreBar({pct}){
  const c=scoreColor(pct);
  return(
    <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
      <div style={{flex:1,height:3,background:T.border,borderRadius:2,overflow:"hidden"}}>
        <div style={{width:`${Math.min(pct,100)}%`,height:"100%",background:c,borderRadius:2,transition:"width 1.1s cubic-bezier(.4,0,.2,1)"}}/>
      </div>
      <span style={{color:c,fontFamily:"'DM Mono',monospace",fontSize:12,fontWeight:600,minWidth:36,textAlign:"right"}}>{Math.round(pct)}%</span>
    </div>
  );
}

function StatPill({label,value}){
  return(
    <div style={{display:"flex",flexDirection:"column",alignItems:"center",padding:"14px 22px",
      background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:10,minWidth:96,
      boxShadow:"0 2px 10px rgba(44,26,14,0.06)"}}>
      <span style={{fontSize:24,fontWeight:700,color:T.orange,fontFamily:"'Playfair Display',serif",lineHeight:1}}>{value}</span>
      <span style={{fontSize:9,color:T.text3,fontFamily:"'DM Mono',monospace",letterSpacing:"0.14em",marginTop:5}}>{label}</span>
    </div>
  );
}

function DetailPanel({item}){
  const d=item.detail||{};
  const tts=parseTT(item.test_type);
  const lvls=item.job_levels?item.job_levels.split("|").map(s=>s.trim()).filter(Boolean):[];
  const langs=item.languages?item.languages.split("|").map(s=>s.trim()).filter(Boolean):[];
  return(
    <div style={{marginTop:18,paddingTop:18,borderTop:`1px dashed ${T.border}`,animation:"fadeIn 0.2s ease"}}>
      {item.description&&<div style={{marginBottom:14}}>
        <div style={{fontSize:9,color:T.text4,fontFamily:"'DM Mono',monospace",letterSpacing:"0.16em",marginBottom:7}}>ABOUT</div>
        <p style={{color:T.text2,fontSize:14,lineHeight:1.75,fontFamily:"'Crimson Pro',Georgia,serif"}}>{item.description}</p>
      </div>}
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:22,marginTop:8}}>
        <div>
          {tts.length>0&&<div style={{marginBottom:12}}>
            <div style={{fontSize:9,color:T.text4,fontFamily:"'DM Mono',monospace",letterSpacing:"0.16em",marginBottom:7}}>TEST TYPES</div>
            <div style={{display:"flex",flexWrap:"wrap",gap:5}}>{tts.map((t,i)=><Tag key={i} color={T.tagDefault}>{t}</Tag>)}</div>
          </div>}
          {lvls.length>0&&<div style={{marginBottom:12}}>
            <div style={{fontSize:9,color:T.text4,fontFamily:"'DM Mono',monospace",letterSpacing:"0.16em",marginBottom:7}}>JOB LEVELS</div>
            <div style={{display:"flex",flexWrap:"wrap",gap:5}}>{lvls.map((t,i)=><Tag key={i} color={T.orange}>{t}</Tag>)}</div>
          </div>}
        </div>
        <div>
          {langs.length>0&&<div style={{marginBottom:12}}>
            <div style={{fontSize:9,color:T.text4,fontFamily:"'DM Mono',monospace",letterSpacing:"0.16em",marginBottom:7}}>LANGUAGES</div>
            <div style={{color:T.text2,fontSize:13,fontFamily:"'Crimson Pro',serif",lineHeight:1.8}}>
              {langs.slice(0,5).join(" · ")}{langs.length>5?` +${langs.length-5} more`:""}
            </div>
          </div>}
          {d.confidence_band&&<Tag color={d.confidence_band==="HIGH"?T.scoreHigh:d.confidence_band==="MEDIUM"?T.scoreMed:T.scoreLow}>{d.confidence_band} QUALITY</Tag>}
        </div>
      </div>
      {item.explain?.length>0&&<div style={{marginTop:12}}>
        <div style={{fontSize:9,color:T.text4,fontFamily:"'DM Mono',monospace",letterSpacing:"0.16em",marginBottom:7}}>MATCH SIGNALS</div>
        <div style={{display:"flex",flexWrap:"wrap",gap:5}}>{item.explain.slice(0,6).map((e,i)=><Tag key={i} color={T.green}>{e.replace(/_/g," ")}</Tag>)}</div>
      </div>}
      {item.url&&item.url!=="nan"&&<div style={{marginTop:16,paddingTop:14,borderTop:`1px dashed ${T.border}`}}>
        <a href={item.url} target="_blank" rel="noreferrer" onClick={e=>e.stopPropagation()}
          style={{color:T.orange,fontSize:13,textDecoration:"none",fontFamily:"'Crimson Pro',serif",
            fontWeight:500,display:"inline-flex",alignItems:"center",gap:6,
            borderBottom:`1px solid ${T.orangeLight}44`,paddingBottom:1}}>
          View on SHL.com →
        </a>
      </div>}
    </div>
  );
}

function ResultCard({item,index}){
  const [open,setOpen]=useState(false);
  const col=familyColor(item.job_family);
  const raw=item.final_score??(item.score!=null?item.score*100:55);
  const pct=Math.min(Math.round(raw),99);
  const tts=parseTT(item.test_type);
  const isRemote=item.remote===true||item.remote_support==="Yes";
  const isAdaptive=item.adaptive===true||item.adaptive_support==="Yes";
  return(
    <div onClick={()=>setOpen(!open)} style={{
      background:T.bgCard,border:`1px solid ${open?T.borderHover:T.border}`,
      borderLeft:`3px solid ${open?col:T.border}`,borderRadius:10,padding:"18px 22px",
      cursor:"pointer",transition:"all 0.18s ease",
      animation:`fadeUp 0.4s ease ${index*0.055}s both`,
      boxShadow:open?"0 6px 24px rgba(44,26,14,0.09)":"0 1px 5px rgba(44,26,14,0.05)"}}
      onMouseEnter={e=>{e.currentTarget.style.background=T.bgCardHover;e.currentTarget.style.borderLeftColor=col;e.currentTarget.style.transform="translateY(-1px)";}}
      onMouseLeave={e=>{e.currentTarget.style.background=T.bgCard;e.currentTarget.style.borderLeftColor=open?col:T.border;e.currentTarget.style.transform="translateY(0)";}}>
      <div style={{display:"flex",alignItems:"flex-start",gap:14}}>
        <div style={{width:28,height:28,borderRadius:6,flexShrink:0,background:T.bgPanel,
          border:`1px solid ${T.border}`,display:"flex",alignItems:"center",justifyContent:"center",
          color:T.text4,fontSize:11,fontFamily:"'DM Mono',monospace",fontWeight:600,marginTop:2}}>{index+1}</div>
        <div style={{flex:1}}>
          <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:10}}>
            <div style={{fontSize:15,fontWeight:600,color:T.text1,fontFamily:"'Playfair Display',serif",letterSpacing:"-0.01em",lineHeight:1.25}}>
              {item.name||item.assessment_name}
            </div>
            <div style={{color:T.text4,fontSize:12,marginLeft:14,flexShrink:0,transition:"transform 0.2s",transform:open?"rotate(180deg)":"rotate(0deg)"}}>▾</div>
          </div>
          <ScoreBar pct={pct}/>
          <div style={{display:"flex",flexWrap:"wrap",gap:5,marginTop:2}}>
            {item.job_family&&<Tag color={col} dot>{item.job_family}</Tag>}
            {isRemote?<Tag color={T.tagIT} dot>Remote</Tag>:<Tag color={T.text4}>On-site</Tag>}
            {isAdaptive&&<Tag color={T.tagBiz} dot>Adaptive IRT</Tag>}
            {item.duration&&<Tag color={T.scoreMed}>⏱ {item.duration} min</Tag>}
            {tts.slice(0,2).map((t,i)=><Tag key={i} color={T.tagDefault}>{t}</Tag>)}
          </div>
        </div>
      </div>
      {open&&<DetailPanel item={item}/>}
    </div>
  );
}

export default function App(){
  const [query,setQuery]=useState("");
  const [results,setResults]=useState([]);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState(null);
  const [mode,setMode]=useState("recommend");
  const [topK,setTopK]=useState(10);
  const [activeFamily,setActiveFamily]=useState("ALL");
  const [searched,setSearched]=useState(false);
  const [filters,setFilters]=useState({remote:"",adaptive:"",max_duration:"",language:"",level_filter:""});
  const inputRef=useRef();
  useEffect(()=>{inputRef.current?.focus();},[]);

  const doSearch=async(overrideQuery)=>{
    const q=overrideQuery||query;
    if(!q.trim())return;
    setLoading(true);setError(null);setResults([]);setActiveFamily("ALL");setSearched(true);
    try{
      // Apply smart rewrite in frontend for immediate effect regardless of API version
      const processed = smartRewrite(q);
      const endpoint=mode==="semantic"?"/semantic-search":"/recommend";
      const body={query:processed,top_k:topK};
      if(mode==="recommend"){
        if(filters.remote!=="")body.remote=filters.remote==="true";
        if(filters.adaptive!=="")body.adaptive=filters.adaptive==="true";
        if(filters.max_duration!=="")body.max_duration=parseInt(filters.max_duration);
        if(filters.language!=="")body.language=filters.language;
        if(filters.level_filter!=="")body.level_filter=filters.level_filter;
      }
      const res=await fetch(`${API_BASE}${endpoint}`,{
        method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)
      });
      const data=await res.json();
      // ══════════════════════════════════════════════════════
      // HANDLES BOTH API FORMATS:
      // New API: { "recommended_assessments": [...] }
      // Old API: { "results": [...] }
      // ══════════════════════════════════════════════════════
      const items=data.recommended_assessments||data.results||[];
      setResults(items);
      if(data.error)setError(`API error: ${data.message||data.error}`);
      else if(items.length===0)setError("No results. Try a different query.");
    }catch(e){
      setError(`Cannot reach API at ${API_BASE}. Run: uvicorn fastapi_api_layer:app --port 8000 --reload`);
    }finally{setLoading(false);}
  };

  const FAMILIES=[
    {label:"ALL",key:null},{label:"IT",key:"Information Technology"},
    {label:"Business",key:"Business"},{label:"Sales",key:"Sales"},
    {label:"Healthcare",key:"Healthcare"},{label:"Contact Ctr",key:"Contact Center"},
  ];
  const displayed=activeFamily==="ALL"?results:results.filter(r=>r.job_family===FAMILIES.find(f=>f.label===activeFamily)?.key);
  const SUGGESTIONS=["Java developer","Data analyst","Leadership assessment","Verbal reasoning","Sales graduate","Python developer","COO cultural fit","Content writer SEO"];

  return(
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Crimson+Pro:ital,wght@0,400;0,500;1,400&family=DM+Mono:wght@400;500&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
        body{background:${T.bg};min-height:100vh;font-family:'Crimson Pro',Georgia,serif;color:${T.text1};-webkit-font-smoothing:antialiased;}
        ::-webkit-scrollbar{width:5px;}::-webkit-scrollbar-track{background:${T.bgPanel};}::-webkit-scrollbar-thumb{background:${T.border};border-radius:3px;}
        @keyframes fadeUp{from{opacity:0;transform:translateY(12px);}to{opacity:1;transform:translateY(0);}}
        @keyframes fadeIn{from{opacity:0;}to{opacity:1;}}
        @keyframes spin{to{transform:rotate(360deg);}}
        @keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.3;}}
        .s-input{flex:1;background:transparent;border:none;outline:none;color:${T.text1};font-size:15px;font-family:'Crimson Pro',serif;}
        .s-input::placeholder{color:${T.text4};font-style:italic;}
        .f-select{width:100%;background:${T.bgCard};border:1px solid ${T.border};color:${T.text2};padding:8px 10px;border-radius:6px;font-family:'DM Mono',monospace;font-size:11px;outline:none;cursor:pointer;transition:border-color 0.15s;appearance:none;}
        .f-select:focus{border-color:${T.orange};}
        .run-btn{padding:0 24px;height:44px;background:${T.orange};color:#FEFCF4;border:none;border-radius:8px;font-family:'DM Mono',monospace;font-size:12px;font-weight:500;letter-spacing:0.07em;cursor:pointer;transition:all 0.15s;white-space:nowrap;}
        .run-btn:hover:not(:disabled){background:${T.orangeHover};box-shadow:0 4px 18px rgba(192,120,74,0.28);transform:translateY(-1px);}
        .run-btn:disabled{opacity:0.35;cursor:not-allowed;}
        .chip{padding:4px 13px;border-radius:20px;font-family:'DM Mono',monospace;font-size:10px;letter-spacing:0.06em;cursor:pointer;border:1px solid transparent;transition:all 0.14s;}
        .chip-on{background:${T.orange};border-color:${T.orange};color:#FEFCF4;}
        .chip-off{background:${T.bgCard};border-color:${T.border};color:${T.text3};}
        .chip-off:hover{border-color:${T.borderHover};color:${T.text2};background:${T.bgPanel};}
        .nav-link{font-size:12px;color:${T.text3};font-family:'DM Mono',monospace;cursor:pointer;transition:color 0.14s;letter-spacing:0.05em;}
        .nav-link:hover{color:${T.orange};}
        .suggest{padding:5px 14px;border-radius:20px;background:${T.bgCard};border:1px solid ${T.border};color:${T.text2};font-size:13px;font-family:'Crimson Pro',serif;cursor:pointer;transition:all 0.14s;font-style:italic;}
        .suggest:hover{border-color:${T.orange};color:${T.orange};background:${T.orangeDim};}
        .sb{display:flex;align-items:center;gap:10px;width:100%;padding:9px 12px;border-radius:7px;border:none;cursor:pointer;font-family:'DM Mono',monospace;font-size:12px;font-weight:500;transition:all 0.14s;text-align:left;letter-spacing:0.03em;}
        .sb-on{background:${T.orange};color:#FEFCF4;}
        .sb-off{background:transparent;color:${T.text3};}
        .sb-off:hover{background:${T.bgCard};color:${T.text2};}
      `}</style>

      <nav style={{height:58,background:T.bgPanel,borderBottom:`1px solid ${T.border}`,display:"flex",alignItems:"center",padding:"0 30px",position:"sticky",top:0,zIndex:100,boxShadow:"0 1px 10px rgba(44,26,14,0.06)"}}>
        <SHLLogo size={22}/>
        <div style={{width:1,height:22,background:T.border,margin:"0 22px"}}/>
        <span style={{fontSize:15,color:T.text2,fontFamily:"'Playfair Display',serif",fontWeight:600}}>Assessment Intelligence</span>
        <div style={{flex:1}}/>
        <div style={{display:"flex",alignItems:"center",gap:26}}>
          {["Dashboard","Catalogue","Analytics"].map(l=><span key={l} className="nav-link">{l}</span>)}
          <div style={{display:"flex",alignItems:"center",gap:7,padding:"6px 14px",borderRadius:20,background:T.bgCard,border:`1px solid ${T.border}`}}>
            <div style={{width:6,height:6,borderRadius:"50%",background:T.green,animation:"pulse 2.5s ease infinite"}}/>
            <span style={{fontSize:10,color:T.text4,fontFamily:"'DM Mono',monospace",letterSpacing:"0.1em"}}>API LIVE</span>
          </div>
        </div>
      </nav>

      <div style={{display:"flex",minHeight:"calc(100vh - 58px)"}}>
        <aside style={{width:232,background:T.bgPanel,borderRight:`1px solid ${T.border}`,padding:"26px 15px",flexShrink:0,display:"flex",flexDirection:"column",gap:5,overflowY:"auto"}}>
          <div style={{fontSize:9,color:T.text4,fontFamily:"'DM Mono',monospace",letterSpacing:"0.15em",marginBottom:8,paddingLeft:8}}>SEARCH MODE</div>
          {[{id:"recommend",icon:"◈",label:"AI Recommend"},{id:"semantic",icon:"⌖",label:"Semantic Search"}].map(({id,icon,label})=>(
            <button key={id} onClick={()=>setMode(id)} className={`sb ${mode===id?"sb-on":"sb-off"}`}>
              <span style={{fontSize:14,opacity:0.85}}>{icon}</span>{label}
            </button>
          ))}
          <div style={{height:1,background:T.border,margin:"14px 0"}}/>
          {mode==="recommend"&&(<>
            <div style={{fontSize:9,color:T.text4,fontFamily:"'DM Mono',monospace",letterSpacing:"0.15em",marginBottom:8,paddingLeft:8}}>FILTERS</div>
            <div style={{marginBottom:12}}>
              <div style={{fontSize:9,color:T.orange,fontFamily:"'DM Mono',monospace",letterSpacing:"0.12em",marginBottom:5,paddingLeft:2}}>JOB LEVEL</div>
              <select className="f-select" value={filters.level_filter} onChange={e=>setFilters(f=>({...f,level_filter:e.target.value}))}>
                <option value="">Any Level</option>
                {JOB_LEVELS.map(l=><option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            {[
              {label:"REMOTE",key:"remote",opts:[["","Any"],["true","Remote Only"],["false","On-site"]]},
              {label:"ADAPTIVE",key:"adaptive",opts:[["","Any"],["true","Yes"],["false","No"]]},
              {label:"DURATION",key:"max_duration",opts:[["","Any"],["15","≤ 15 min"],["30","≤ 30 min"],["45","≤ 45 min"],["60","≤ 60 min"]]},
              {label:"LANGUAGE",key:"language",opts:[["","Any"],["English","English"],["French","French"],["German","German"],["Spanish","Spanish"]]},
            ].map(({label,key,opts})=>(
              <div key={key} style={{marginBottom:12}}>
                <div style={{fontSize:9,color:T.text4,fontFamily:"'DM Mono',monospace",letterSpacing:"0.12em",marginBottom:5,paddingLeft:2}}>{label}</div>
                <select className="f-select" value={filters[key]} onChange={e=>setFilters(f=>({...f,[key]:e.target.value}))}>
                  {opts.map(([v,l])=><option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            ))}
            <div style={{marginBottom:12}}>
              <div style={{fontSize:9,color:T.text4,fontFamily:"'DM Mono',monospace",letterSpacing:"0.12em",marginBottom:5,paddingLeft:2,display:"flex",justifyContent:"space-between"}}>
                <span>TOP K</span><span style={{color:T.orange,fontWeight:500}}>{topK}</span>
              </div>
              <input type="range" min={1} max={10} value={topK} onChange={e=>setTopK(parseInt(e.target.value))} style={{width:"100%",accentColor:T.orange,cursor:"pointer"}}/>
            </div>
          </>)}
          <div style={{flex:1}}/>
          <div style={{padding:"12px 8px",borderTop:`1px solid ${T.border}`}}>
            <div style={{fontSize:9,color:T.text5,fontFamily:"'DM Mono',monospace",lineHeight:2,letterSpacing:"0.09em"}}>
              VECTOR INDEX READY<br/>FAISS LOADED<br/>RERANKER ACTIVE
            </div>
          </div>
        </aside>

        <main style={{flex:1,padding:"32px 36px",overflowY:"auto",minWidth:0}}>
          {!searched&&(
            <div style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",minHeight:"calc(100vh - 180px)",animation:"fadeIn 0.7s ease"}}>
              <SHLLogo size={70}/>
              <h1 style={{marginTop:24,marginBottom:10,fontSize:34,fontWeight:700,color:T.text1,fontFamily:"'Playfair Display',serif",letterSpacing:"-0.02em",textAlign:"center"}}>Assessment Intelligence</h1>
              <p style={{fontSize:16,color:T.text3,fontFamily:"'Crimson Pro',serif",marginBottom:44,textAlign:"center",maxWidth:420,lineHeight:1.8,fontStyle:"italic"}}>
                Find the right SHL assessment for any role.<br/>Powered by semantic search &amp; AI ranking.
              </p>
              <div style={{display:"flex",gap:12,marginBottom:48}}>
                <StatPill label="ASSESSMENTS" value="377"/>
                <StatPill label="TEST TYPES" value="8"/>
                <StatPill label="LANGUAGES" value="50+"/>
                <StatPill label="JOB LEVELS" value="10"/>
              </div>
              <div style={{width:"100%",maxWidth:600}}>
                <div style={{display:"flex",gap:10}}>
                  <div style={{flex:1,display:"flex",alignItems:"center",gap:12,background:T.bgInput,
                    border:`1px solid ${T.border}`,borderRadius:10,padding:"0 16px",height:50,
                    transition:"border-color 0.15s, box-shadow 0.15s",boxShadow:"0 2px 10px rgba(44,26,14,0.05)"}}
                    onFocusCapture={e=>{e.currentTarget.style.borderColor=T.orange;e.currentTarget.style.boxShadow=`0 0 0 3px ${T.orangeGlow}`;}}
                    onBlurCapture={e=>{e.currentTarget.style.borderColor=T.border;e.currentTarget.style.boxShadow="0 2px 10px rgba(44,26,14,0.05)";}}>
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke={T.text4} strokeWidth={2}><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                    <input ref={inputRef} className="s-input"
                      placeholder="e.g. 'Java developer', 'data analyst', 'verbal reasoning'…"
                      value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")doSearch();}}/>
                    {query&&<button onClick={()=>setQuery("")} style={{background:"none",border:"none",color:T.text4,cursor:"pointer",fontSize:14}}>✕</button>}
                  </div>
                  <button className="run-btn" onClick={()=>doSearch()} disabled={loading||!query.trim()}>
                    {loading?"…":"RECOMMEND"}
                  </button>
                </div>
                <div style={{marginTop:14,display:"flex",gap:8,flexWrap:"wrap",justifyContent:"center"}}>
                  {SUGGESTIONS.map(s=>(
                    <span key={s} className="suggest" onClick={()=>{setQuery(s);doSearch(s);}}>{s}</span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {searched&&(<>
            <div style={{display:"flex",gap:10,marginBottom:16,animation:"fadeUp 0.3s ease"}}>
              <div style={{flex:1,display:"flex",alignItems:"center",gap:12,background:T.bgInput,
                border:`1px solid ${T.border}`,borderRadius:10,padding:"0 16px",height:46,
                transition:"border-color 0.15s"}}
                onFocusCapture={e=>e.currentTarget.style.borderColor=T.orange}
                onBlurCapture={e=>e.currentTarget.style.borderColor=T.border}>
                <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke={T.text4} strokeWidth={2}><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                <input className="s-input"
                  placeholder={mode==="recommend"?"Describe the role or paste JD…":"Search by name or skill…"}
                  value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")doSearch();}}/>
                {query&&<button onClick={()=>{setQuery("");setResults([]);setSearched(false);}} style={{background:"none",border:"none",color:T.text4,cursor:"pointer",fontSize:14}}>✕</button>}
              </div>
              <button className="run-btn" onClick={()=>doSearch()} disabled={loading||!query.trim()}>
                {loading?"…":mode==="recommend"?"RECOMMEND":"SEARCH"}
              </button>
            </div>

            {loading&&<div style={{textAlign:"center",padding:"70px 0",animation:"fadeIn 0.3s ease"}}>
              <div style={{width:30,height:30,border:`2px solid ${T.border}`,borderTopColor:T.orange,borderRadius:"50%",animation:"spin 0.8s linear infinite",margin:"0 auto 16px"}}/>
              <div style={{color:T.text4,fontFamily:"'DM Mono',monospace",fontSize:11,letterSpacing:"0.14em"}}>RUNNING AI PIPELINE…</div>
            </div>}

            {error&&<div style={{background:"#B8484018",border:`1px solid #B8484030`,borderRadius:8,padding:"14px 18px",marginBottom:18,color:T.scoreLow,fontFamily:"'DM Mono',monospace",fontSize:12,display:"flex",gap:10,alignItems:"center"}}>
              <span>⚠</span>{error}
            </div>}

            {results.length>0&&!loading&&(<>
              <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:12,flexWrap:"wrap",gap:10}}>
                <div style={{fontSize:15,color:T.text2,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>
                  Showing <strong style={{fontStyle:"normal",color:T.text1}}>{displayed.length}</strong> results
                  {query&&<> for <strong style={{fontStyle:"normal",color:T.orange}}>"{query}"</strong></>}
                </div>
                <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
                  {FAMILIES.map(({label,key})=>{
                    const count=key===null?results.length:results.filter(r=>r.job_family===key).length;
                    if(count===0&&key!==null)return null;
                    const on=activeFamily===label;
                    return<span key={label} className={`chip ${on?"chip-on":"chip-off"}`} onClick={()=>setActiveFamily(label)}>
                      {label} <span style={{opacity:0.65}}>{count}</span>
                    </span>;
                  })}
                </div>
              </div>
              <div style={{height:1,background:T.border,marginBottom:14}}/>
            </>)}

            {!loading&&<div style={{display:"flex",flexDirection:"column",gap:10}}>
              {displayed.map((item,i)=><ResultCard key={`${item.id||item.name||i}`} item={item} index={i}/>)}
            </div>}

            {!loading&&!error&&results.length===0&&<div style={{textAlign:"center",padding:"70px 0",animation:"fadeIn 0.4s ease"}}>
              <div style={{fontSize:40,color:T.border,marginBottom:14}}>◎</div>
              <div style={{color:T.text2,fontFamily:"'Playfair Display',serif",fontSize:20,marginBottom:6}}>No results found</div>
              <div style={{color:T.text4,fontFamily:"'Crimson Pro',serif",fontSize:14,fontStyle:"italic"}}>Try broader keywords or remove active filters</div>
            </div>}
          </>)}
        </main>
      </div>
    </>
  );
}