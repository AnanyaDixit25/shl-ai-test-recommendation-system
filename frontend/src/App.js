import { useState, useRef, useEffect } from "react";

const API_BASE = "http://127.0.0.1:8000";

const T = {
  bg:          "#8f7462",
  bgCard:      "#231508",
  bgCardHover: "#2A1A0A",
  bgPanel:     "#180E06",
  bgInput:     "#201208",
  border:      "#3A2510",
  borderHover: "#4A3018",
  borderFocus: "#6BBF4E55",

  green:       "#6BBF4E",
  greenHover:  "#4be513",
  greenGlow:   "#6BBF4E22",
  greenDim:    "#6BBF4E14",

  grey1:       "#F5EDE0",
  grey2:       "#C4A882",
  grey3:       "#f1a048",
  grey4:       "#f89050",
  grey5:       "#3A2518",

  scoreHigh:   "#6BBF4E",
  scoreMed:    "#E8A838",
  scoreLow:    "#E05252",

  tagIT:       "#5AAEEA",
  tagBiz:      "#B07ED4",
  tagSales:    "#E8923A",
  tagHealth:   "#4ABF8A",
  tagDefault:  "#7A6050",
};

const familyColor = (f) => ({
  "Information Technology": T.tagIT,
  "Business":               T.tagBiz,
  "Sales":                  T.tagSales,
  "Healthcare":             T.tagHealth,
  "Contact Center":         T.scoreMed,
  "Clerical":               "#907060",
  "Safety":                 T.scoreLow,
}[f] || T.tagDefault);

const scoreColor = (p) => p >= 70 ? T.scoreHigh : p >= 45 ? T.scoreMed : T.scoreLow;

function SHLLogo({ size = 48 }) {
  return (
    <svg width={size * 2.8} height={size} viewBox="0 0 140 50" fill="none">
      <path d="M8 36 C8 40 12 43 18 43 C24 43 28 40 28 35 C28 30 24 28 18 26 C12 24 8 22 8 17 C8 12 12 8 18 8 C24 8 28 12 28 16"
        stroke="#7A6050" strokeWidth="5" strokeLinecap="round" fill="none"/>
      <path d="M36 8 L36 43 M36 26 L54 26 M54 8 L54 43"
        stroke="#7A6050" strokeWidth="5" strokeLinecap="round"/>
      <path d="M62 8 L62 43 L80 43"
        stroke="#7A6050" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="90" cy="43" r="5.5" fill="#6BBF4E"/>
    </svg>
  );
}

function ScoreBar({ pct }) {
  const c = scoreColor(pct);
  return (
    <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
      <div style={{ flex:1, height:2, background:T.border, borderRadius:1, overflow:"hidden" }}>
        <div style={{
          width:`${Math.min(pct,100)}%`, height:"100%", background:c, borderRadius:1,
          transition:"width 1s cubic-bezier(.4,0,.2,1)", boxShadow:`0 0 8px ${c}88`,
        }}/>
      </div>
      <span style={{ color:c, fontFamily:"'JetBrains Mono','DM Mono',monospace", fontSize:12, fontWeight:700, minWidth:36, textAlign:"right" }}>
        {Math.round(pct)}%
      </span>
    </div>
  );
}

function Tag({ children, color = T.tagDefault, dot }) {
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", gap:5,
      padding:"2px 8px", borderRadius:3, fontSize:11, fontWeight:500,
      background:`${color}18`, color, border:`1px solid ${color}35`,
      fontFamily:"'JetBrains Mono','DM Mono',monospace",
      letterSpacing:"0.02em", whiteSpace:"nowrap",
    }}>
      {dot && <span style={{ width:5, height:5, borderRadius:"50%", background:color, flexShrink:0 }}/>}
      {children}
    </span>
  );
}

function StatPill({ label, value }) {
  return (
    <div style={{
      display:"flex", flexDirection:"column", alignItems:"center",
      padding:"10px 20px", background:T.bgPanel,
      border:`1px solid ${T.border}`, borderRadius:6, minWidth:90,
    }}>
      <span style={{ fontSize:18, fontWeight:700, color:T.grey1, fontFamily:"'Inter',sans-serif", lineHeight:1 }}>{value}</span>
      <span style={{ fontSize:9, color:T.grey3, fontFamily:"'JetBrains Mono',monospace", letterSpacing:"0.1em", marginTop:4 }}>{label}</span>
    </div>
  );
}

function DetailBlock({ label, children }) {
  return (
    <div style={{ marginBottom:12 }}>
      <div style={{ fontSize:9, color:T.grey4, fontFamily:"'JetBrains Mono',monospace", letterSpacing:"0.12em", marginBottom:5 }}>{label}</div>
      {children}
    </div>
  );
}

function MiniStat({ label, val }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
      <span style={{ fontSize:9, color:T.grey4, fontFamily:"'JetBrains Mono',monospace", letterSpacing:"0.1em" }}>{label.toUpperCase()}</span>
      <span style={{ fontSize:12, color:scoreColor(val), fontFamily:"'JetBrains Mono',monospace", fontWeight:700 }}>{val}%</span>
    </div>
  );
}

function ResultCard({ item, index }) {
  const [open, setOpen] = useState(false);
  const fc   = familyColor(item.job_family);
  const raw  = item.final_score ?? (item.score != null ? item.score * 100 : 0);
  const pct  = Math.min(Math.round(raw), 99);
  const tts  = item.test_type ? item.test_type.split("|").map(s=>s.trim()).filter(Boolean) : [];
  const lvls = item.job_levels ? item.job_levels.split("|").map(s=>s.trim()).filter(Boolean) : [];
  const sc   = scoreColor(pct);

  return (
    <div
      style={{
        background:T.bgCard, border:`1px solid ${open ? T.borderHover : T.border}`,
        borderLeft:`3px solid ${open ? fc : T.border}`,
        borderRadius:6, padding:"16px 20px", cursor:"pointer",
        transition:"all 0.18s ease",
        animation:`fadeUp 0.4s ease ${index*0.055}s both`,
      }}
      onMouseEnter={e=>{
        e.currentTarget.style.background=T.bgCardHover;
        e.currentTarget.style.borderLeftColor=fc;
        e.currentTarget.style.transform="translateX(3px)";
      }}
      onMouseLeave={e=>{
        e.currentTarget.style.background=T.bgCard;
        e.currentTarget.style.borderLeftColor=open?fc:T.border;
        e.currentTarget.style.transform="translateX(0)";
      }}
      onClick={()=>setOpen(!open)}
    >
      <div style={{ display:"flex", alignItems:"flex-start", gap:12 }}>
        <div style={{
          width:26, height:26, borderRadius:4, flexShrink:0,
          background:T.bgPanel, border:`1px solid ${T.border}`,
          display:"flex", alignItems:"center", justifyContent:"center",
          color:T.grey4, fontSize:10, fontFamily:"'JetBrains Mono',monospace",
          fontWeight:700, marginTop:1,
        }}>{index+1}</div>

        <div style={{ flex:1 }}>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:8 }}>
            <div style={{
              fontSize:14, fontWeight:600, color:T.grey1,
              fontFamily:"'Inter',sans-serif", letterSpacing:"-0.01em", lineHeight:1.2,
            }}>
              {item.name || item.assessment_name}
            </div>
            <div style={{
              color:T.grey4, fontSize:11, marginLeft:12, flexShrink:0,
              transition:"transform 0.2s", transform:open?"rotate(180deg)":"rotate(0deg)",
            }}>▾</div>
          </div>

          <ScoreBar pct={pct}/>

          <div style={{ display:"flex", flexWrap:"wrap", gap:5 }}>
            {item.job_family && <Tag color={fc} dot>{item.job_family}</Tag>}
            {(item.remote===true||item.remote==="true"||item.remote==="True")
              ? <Tag color={T.tagIT} dot>Remote</Tag>
              : <Tag color={T.grey4}>On-site</Tag>}
            {(item.adaptive===true||item.adaptive==="true"||item.adaptive==="True") && (
              <Tag color={T.tagBiz} dot>Adaptive IRT</Tag>
            )}
            {item.duration && item.duration!=="" && (
              <Tag color={T.grey3}>⏱ {item.duration} min</Tag>
            )}
            {tts.slice(0,2).map((t,i)=><Tag key={i} color={T.tagDefault}>{t}</Tag>)}
          </div>
        </div>
      </div>

      {open && (
        <div style={{ marginTop:16, paddingTop:16, borderTop:`1px solid ${T.border}`, animation:"fadeIn 0.2s ease" }}>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>
            <div>
              {lvls.length>0 && (
                <DetailBlock label="JOB LEVELS">
                  <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
                    {lvls.map((l,i)=><Tag key={i} color={T.grey3}>{l}</Tag>)}
                  </div>
                </DetailBlock>
              )}
              {tts.length>0 && (
                <DetailBlock label="TEST TYPES">
                  <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
                    {tts.map((t,i)=><Tag key={i} color={T.tagDefault}>{t}</Tag>)}
                  </div>
                </DetailBlock>
              )}
              {item.languages && (
                <DetailBlock label="LANGUAGES">
                  <span style={{ color:T.grey2, fontSize:12 }}>
                    {item.languages.split("|").slice(0,5).join(", ")}
                    {item.languages.split("|").length>5?"…":""}
                  </span>
                </DetailBlock>
              )}
            </div>
            <div>
              <DetailBlock label="CONFIDENCE">
                <div style={{ display:"flex", gap:3, alignItems:"center" }}>
                  {[1,2,3,4,5].map(i=>(
                    <div key={i} style={{
                      width:20, height:4, borderRadius:2,
                      background:i<=Math.round((pct/100)*5)?sc:T.border,
                      transition:"background 0.3s",
                    }}/>
                  ))}
                  <span style={{ color:T.grey3, fontSize:11, marginLeft:6 }}>
                    {pct>=70?"High":pct>=45?"Medium":"Low"}
                  </span>
                </div>
              </DetailBlock>

              {item.explain && item.explain.length>0 && (
                <DetailBlock label="MATCH SIGNALS">
                  <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
                    {item.explain.slice(0,4).map((e,i)=>(
                      <Tag key={i} color={T.green}>{e.replace(/_/g," ")}</Tag>
                    ))}
                  </div>
                </DetailBlock>
              )}

              {item.url && item.url!=="nan" && item.url!=="" && (
                <DetailBlock label="REFERENCE">
                  
                    href={item.url} target="_blank" rel="noreferrer"
                    onClick={e=>e.stopPropagation()}
                    style={{ color:T.tagIT, fontSize:12, textDecoration:"none", fontFamily:"'JetBrains Mono',monospace" }}
                    onMouseEnter={e=>e.currentTarget.style.textDecoration="underline"}
                    onMouseLeave={e=>e.currentTarget.style.textDecoration="none"}
                  <a>View on SHL →</a>
                </DetailBlock>
              )}
            </div>
          </div>

          {(item.semantic_score!=null||item.keyword_score!=null) && (
            <div style={{ display:"flex", gap:24, marginTop:12, padding:"10px 14px", background:T.bgPanel, borderRadius:5, border:`1px solid ${T.border}` }}>
              {item.semantic_score!=null && <MiniStat label="Semantic" val={Math.round(item.semantic_score*100)}/>}
              {item.keyword_score!=null  && <MiniStat label="Keyword"  val={Math.round(item.keyword_score*100)}/>}
              {item.intent_score!=null   && <MiniStat label="Intent"   val={Math.round(item.intent_score*100)}/>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [query,setQuery]               = useState("");
  const [results,setResults]           = useState([]);
  const [loading,setLoading]           = useState(false);
  const [error,setError]               = useState(null);
  const [mode,setMode]                 = useState("recommend");
  const [topK,setTopK]                 = useState(10);
  const [activeFamily,setActiveFamily] = useState("ALL");
  const [searched,setSearched]         = useState(false);
  const [filters,setFilters]           = useState({ remote:"", adaptive:"", max_duration:"", language:"" });
  const inputRef = useRef();

  useEffect(()=>{ inputRef.current?.focus(); },[]);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true); setError(null); setResults([]); setActiveFamily("ALL"); setSearched(true);
    try {
      const endpoint = mode==="semantic" ? "/semantic-search" : "/recommend";
      const body = { query, top_k:topK };
      if (mode==="recommend") {
        if (filters.remote!=="")       body.remote       = filters.remote==="true";
        if (filters.adaptive!=="")     body.adaptive     = filters.adaptive==="true";
        if (filters.max_duration!=="") body.max_duration = parseInt(filters.max_duration);
        if (filters.language!=="")     body.language     = filters.language;
      }
      const res = await fetch(`${API_BASE}${endpoint}`,{
        method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body),
      });
      const data = await res.json();
      setResults(data.results||[]);
    } catch {
      setError("Unable to reach API. Make sure FastAPI is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e)=>{ if(e.key==="Enter") handleSearch(); };

  const setQueryAndSearch = (s) => {
    setQuery(s);
    setTimeout(async () => {
      if (!s.trim()) return;
      setLoading(true); setError(null); setResults([]); setActiveFamily("ALL"); setSearched(true);
      try {
        const res = await fetch(`${API_BASE}/recommend`,{
          method:"POST", headers:{"Content-Type":"application/json"},
          body:JSON.stringify({ query:s, top_k:topK }),
        });
        const data = await res.json();
        setResults(data.results||[]);
      } catch { setError("Unable to reach API."); }
      finally { setLoading(false); }
    }, 50);
  };

  const FAMILIES = [
    { label:"ALL",         key:null },
    { label:"IT",          key:"Information Technology" },
    { label:"Business",    key:"Business" },
    { label:"Sales",       key:"Sales" },
    { label:"Healthcare",  key:"Healthcare" },
    { label:"Contact Ctr", key:"Contact Center" },
  ];

  const displayed = activeFamily==="ALL"
    ? results
    : results.filter(r=>r.job_family===FAMILIES.find(f=>f.label===activeFamily)?.key);

  const SUGGESTIONS = [
    "Java developer", "Data science", "Leadership assessment",
    "Verbal reasoning", "Sales manager", "Python developer",
  ];

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
        *,*::before,*::after { box-sizing:border-box; margin:0; padding:0; }
        body { background:${T.bg}; min-height:100vh; font-family:'Inter',system-ui,sans-serif; color:${T.grey1}; -webkit-font-smoothing:antialiased; }
        ::selection { background:${T.greenGlow}; color:#fff; }
        ::-webkit-scrollbar { width:4px; }
        ::-webkit-scrollbar-track { background:${T.bg}; }
        ::-webkit-scrollbar-thumb { background:${T.grey5}; border-radius:2px; }
        @keyframes fadeUp { from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);} }
        @keyframes fadeIn { from{opacity:0;}to{opacity:1;} }
        @keyframes spin   { to{transform:rotate(360deg);} }
        @keyframes pulseGreen { 0%,100%{opacity:1;}50%{opacity:0.4;} }

        .s-input { flex:1; background:transparent; border:none; outline:none; color:${T.grey1}; font-size:15px; font-family:'Inter',sans-serif; }
        .s-input::placeholder { color:${T.grey4}; }

        .f-select { width:100%; background:${T.bgPanel}; border:1px solid ${T.border}; color:${T.grey2}; padding:8px 10px; border-radius:5px; font-family:'JetBrains Mono',monospace; font-size:11px; outline:none; cursor:pointer; transition:border-color 0.15s; appearance:none; }
        .f-select:focus { border-color:${T.borderHover}; }

        .run-btn { padding:0 24px; height:44px; background:${T.green}; color:#0A0A0A; border:none; border-radius:5px; font-family:'Inter',sans-serif; font-size:13px; font-weight:700; letter-spacing:0.03em; cursor:pointer; transition:all 0.15s; white-space:nowrap; }
        .run-btn:hover:not(:disabled) { background:${T.greenHover}; box-shadow:0 0 20px ${T.greenGlow}; transform:translateY(-1px); }
        .run-btn:disabled { opacity:0.3; cursor:not-allowed; }

        .tab { padding:6px 16px; border-radius:4px; font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:500; letter-spacing:0.05em; cursor:pointer; border:1px solid transparent; transition:all 0.15s; background:none; }
        .tab-on  { background:${T.greenDim}; border-color:${T.green}40; color:${T.green}; }
        .tab-off { border-color:${T.border}; color:${T.grey4}; }
        .tab-off:hover { color:${T.grey3}; border-color:${T.borderHover}; }

        .chip { padding:3px 10px; border-radius:3px; font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.05em; cursor:pointer; border:1px solid transparent; transition:all 0.12s; }
        .chip-on  { background:${T.greenDim}; border-color:${T.green}40; color:${T.green}; }
        .chip-off { background:${T.bgPanel}; border-color:${T.border}; color:${T.grey4}; }
        .chip-off:hover { color:${T.grey3}; border-color:${T.borderHover}; }

        .nav-link { font-size:12px; color:${T.grey4}; font-family:'Inter',sans-serif; cursor:pointer; transition:color 0.15s; text-decoration:none; }
        .nav-link:hover { color:${T.grey2}; }

        .suggest { padding:4px 12px; border-radius:3px; background:${T.bgPanel}; border:1px solid ${T.border}; color:${T.grey3}; font-size:11px; font-family:'JetBrains Mono',monospace; cursor:pointer; transition:all 0.15s; }
        .suggest:hover { border-color:${T.borderHover}; color:${T.grey2}; background:${T.bgCard}; }

        .sidebar-btn { display:flex; align-items:center; gap:10; width:100%; padding:9px 12px; border-radius:5px; border:none; cursor:pointer; font-family:'Inter',sans-serif; font-size:13px; font-weight:500; transition:all 0.15s; text-align:left; }
        .sidebar-btn-on  { background:${T.greenDim}; color:${T.green}; outline:1px solid ${T.green}30; }
        .sidebar-btn-off { background:transparent; color:${T.grey3}; }
        .sidebar-btn-off:hover { background:${T.grey5}; color:${T.grey2}; }
      `}</style>

      {/* ── Top Nav ── */}
      <nav style={{
        height:56, background:T.bgPanel, borderBottom:`1px solid ${T.border}`,
        display:"flex", alignItems:"center", padding:"0 28px",
        position:"sticky", top:0, zIndex:100,
      }}>
        <SHLLogo size={22}/>
        <div style={{ width:1, height:24, background:T.border, margin:"0 22px" }}/>
        <span style={{ fontSize:13, color:T.grey3, fontFamily:"'Inter',sans-serif", fontWeight:500 }}>
          Assessment Intelligence
        </span>
        <div style={{ flex:1 }}/>
        <div style={{ display:"flex", alignItems:"center", gap:22 }}>
          <span className="nav-link">Dashboard</span>
          <span className="nav-link">Catalogue</span>
          <span className="nav-link">Analytics</span>
          <div style={{ display:"flex", alignItems:"center", gap:6, padding:"5px 12px", borderRadius:20, background:T.bg, border:`1px solid ${T.border}` }}>
            <div style={{ width:6, height:6, borderRadius:"50%", background:T.green, animation:"pulseGreen 2s ease infinite" }}/>
            <span style={{ fontSize:10, color:T.grey4, fontFamily:"'JetBrains Mono',monospace", letterSpacing:"0.08em" }}>API LIVE</span>
          </div>
        </div>
      </nav>

      <div style={{ display:"flex", minHeight:"calc(100vh - 56px)" }}>

        {/* ── Sidebar ── */}
        <aside style={{
          width:220, background:T.bgPanel, borderRight:`1px solid ${T.border}`,
          padding:"24px 14px", flexShrink:0, display:"flex", flexDirection:"column", gap:6,
        }}>
          <div style={{ fontSize:9, color:T.grey4, fontFamily:"'JetBrains Mono',monospace", letterSpacing:"0.12em", marginBottom:8, paddingLeft:8 }}>SEARCH MODE</div>

          {[
            { id:"recommend", icon:"◈", label:"AI Recommend" },
            { id:"semantic",  icon:"⌖", label:"Semantic Search" },
          ].map(({ id, icon, label })=>(
            <button key={id} onClick={()=>setMode(id)}
              className={`sidebar-btn ${mode===id?"sidebar-btn-on":"sidebar-btn-off"}`}
            >
              <span style={{ fontSize:14, opacity:0.8 }}>{icon}</span>{label}
            </button>
          ))}

          <div style={{ height:1, background:T.border, margin:"12px 0" }}/>

          {mode==="recommend" && (
            <>
              <div style={{ fontSize:9, color:T.grey4, fontFamily:"'JetBrains Mono',monospace", letterSpacing:"0.12em", marginBottom:8, paddingLeft:8 }}>FILTERS</div>
              {[
                { label:"REMOTE",   key:"remote",       opts:[["","Any"],["true","Remote Only"],["false","On-site Only"]] },
                { label:"ADAPTIVE", key:"adaptive",      opts:[["","Any"],["true","Yes"],["false","No"]] },
                { label:"DURATION", key:"max_duration",  opts:[["","Any"],["15","≤ 15 min"],["30","≤ 30 min"],["45","≤ 45 min"],["60","≤ 60 min"],["90","≤ 90 min"]] },
                { label:"LANGUAGE", key:"language",      opts:[["","Any"],["English","English"],["French","French"],["German","German"],["Spanish","Spanish"]] },
              ].map(({ label, key, opts })=>(
                <div key={key} style={{ marginBottom:10 }}>
                  <div style={{ fontSize:9, color:T.grey4, fontFamily:"'JetBrains Mono',monospace", letterSpacing:"0.1em", marginBottom:5, paddingLeft:2 }}>{label}</div>
                  <select className="f-select" value={filters[key]} onChange={e=>setFilters(f=>({...f,[key]:e.target.value}))}>
                    {opts.map(([v,l])=><option key={v} value={v}>{l}</option>)}
                  </select>
                </div>
              ))}
              <div style={{ marginBottom:10 }}>
                <div style={{ fontSize:9, color:T.grey4, fontFamily:"'JetBrains Mono',monospace", letterSpacing:"0.1em", marginBottom:5, paddingLeft:2, display:"flex", justifyContent:"space-between" }}>
                  <span>TOP K</span><span style={{ color:T.green }}>{topK}</span>
                </div>
                <input type="range" min={1} max={20} value={topK} onChange={e=>setTopK(parseInt(e.target.value))} style={{ width:"100%", accentColor:T.green, cursor:"pointer" }}/>
              </div>
            </>
          )}

          <div style={{ flex:1 }}/>
          <div style={{ padding:"10px 8px", borderTop:`1px solid ${T.border}` }}>
            <div style={{ fontSize:9, color:T.grey5, fontFamily:"'JetBrains Mono',monospace", lineHeight:1.8 }}>
              VECTOR INDEX READY<br/>FAISS LOADED<br/>RERANKER STANDBY
            </div>
          </div>
        </aside>

        {/* ── Main ── */}
        <main style={{ flex:1, padding:"28px 32px", overflowY:"auto", minWidth:0 }}>

          {/* Hero empty state */}
          {!searched && (
            <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", minHeight:"calc(100vh - 160px)", animation:"fadeIn 0.6s ease" }}>
              <SHLLogo size={64}/>
              <div style={{ marginTop:20, marginBottom:8, fontSize:22, fontWeight:700, color:T.grey1, fontFamily:"'Inter',sans-serif", letterSpacing:"-0.02em" }}>
                Assessment Intelligence
              </div>
              <div style={{ fontSize:13, color:T.grey3, fontFamily:"'Inter',sans-serif", marginBottom:40, textAlign:"center", maxWidth:400, lineHeight:1.7 }}>
                AI-powered recommendation engine for SHL assessments.<br/>
                Enter a role or skill below to find the most relevant tests.
              </div>

              <div style={{ display:"flex", gap:10, marginBottom:40 }}>
                <StatPill label="ASSESSMENTS" value="400+"/>
                <StatPill label="TEST TYPES"  value="8"/>
                <StatPill label="LANGUAGES"   value="50+"/>
                <StatPill label="MODEL"       value="v2"/>
              </div>

              <div style={{ width:"100%", maxWidth:560 }}>
                <div style={{ display:"flex", gap:10 }}>
                  <div style={{
                    flex:1, display:"flex", alignItems:"center", gap:10,
                    background:T.bgInput, border:`1px solid ${T.border}`,
                    borderRadius:6, padding:"0 14px", height:46,
                    transition:"border-color 0.15s, box-shadow 0.15s",
                  }}
                    onFocusCapture={e=>{e.currentTarget.style.borderColor=T.green+"60";e.currentTarget.style.boxShadow=`0 0 0 3px ${T.greenGlow}`;}}
                    onBlurCapture={e=>{e.currentTarget.style.borderColor=T.border;e.currentTarget.style.boxShadow="none";}}
                  >
                    <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke={T.grey4} strokeWidth={2.5}>
                      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                    </svg>
                    <input ref={inputRef} className="s-input"
                      placeholder="e.g. 'Java developer', 'data science', 'verbal reasoning'…"
                      value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={handleKey}
                    />
                    {query && <button onClick={()=>{setQuery("");}} style={{ background:"none",border:"none",color:T.grey4,cursor:"pointer",fontSize:13 }}>✕</button>}
                  </div>
                  <button className="run-btn" onClick={handleSearch} disabled={loading||!query.trim()}>
                    {loading?"…":"RECOMMEND"}
                  </button>
                </div>

                <div style={{ marginTop:10, display:"flex", gap:6, flexWrap:"wrap" }}>
                  {SUGGESTIONS.map(s=>(
                    <span key={s} className="suggest" onClick={()=>setQueryAndSearch(s)}>{s}</span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Post-search */}
          {searched && (
            <>
              <div style={{ display:"flex", gap:10, marginBottom:20, animation:"fadeUp 0.3s ease" }}>
                <div style={{
                  flex:1, display:"flex", alignItems:"center", gap:10,
                  background:T.bgInput, border:`1px solid ${T.border}`,
                  borderRadius:6, padding:"0 14px", height:44,
                  transition:"border-color 0.15s, box-shadow 0.15s",
                }}
                  onFocusCapture={e=>{e.currentTarget.style.borderColor=T.green+"60";e.currentTarget.style.boxShadow=`0 0 0 3px ${T.greenGlow}`;}}
                  onBlurCapture={e=>{e.currentTarget.style.borderColor=T.border;e.currentTarget.style.boxShadow="none";}}
                >
                  <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke={T.grey4} strokeWidth={2.5}>
                    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                  </svg>
                  <input className="s-input"
                    placeholder={mode==="recommend"?"Describe the role or skill…":"Search by name or skill…"}
                    value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={handleKey}
                  />
                  {query && (
                    <button onClick={()=>{setQuery("");setResults([]);setSearched(false);}} style={{ background:"none",border:"none",color:T.grey4,cursor:"pointer",fontSize:13 }}>✕</button>
                  )}
                </div>
                <button className="run-btn" onClick={handleSearch} disabled={loading||!query.trim()}>
                  {loading?"…":mode==="recommend"?"RECOMMEND":"SEARCH"}
                </button>
              </div>

              {loading && (
                <div style={{ textAlign:"center", padding:"60px 0", animation:"fadeIn 0.3s ease" }}>
                  <div style={{ width:28,height:28,border:`2px solid ${T.border}`,borderTopColor:T.green,borderRadius:"50%",animation:"spin 0.7s linear infinite",margin:"0 auto 14px" }}/>
                  <div style={{ color:T.grey4,fontFamily:"'JetBrains Mono',monospace",fontSize:11,letterSpacing:"0.12em" }}>
                    {mode==="recommend"?"RUNNING AI PIPELINE…":"QUERYING VECTOR INDEX…"}
                  </div>
                </div>
              )}

              {error && (
                <div style={{ background:"#E0525210",border:"1px solid #E0525230",borderRadius:5,padding:"12px 16px",marginBottom:16,color:"#E05252",fontFamily:"'JetBrains Mono',monospace",fontSize:12,display:"flex",gap:8,alignItems:"center" }}>
                  <span>⚠</span>{error}
                </div>
              )}

              {results.length>0 && !loading && (
                <>
                  <div style={{ display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:10,flexWrap:"wrap",gap:8 }}>
                    <div style={{ fontFamily:"'JetBrains Mono',monospace",fontSize:10,color:T.grey4,letterSpacing:"0.1em" }}>
                      {displayed.length} RESULTS &nbsp;·&nbsp;
                      {mode==="recommend"?"AI RERANKED":"SEMANTIC FAISS"}
                      &nbsp;·&nbsp;
                      <span style={{ color:T.green }}>"{query}"</span>
                    </div>
                    <div style={{ display:"flex",gap:5,flexWrap:"wrap" }}>
                      {FAMILIES.map(({ label,key })=>{
                        const count = key===null?results.length:results.filter(r=>r.job_family===key).length;
                        if(count===0&&key!==null) return null;
                        const on = activeFamily===label;
                        return (
                          <span key={label} className={`chip ${on?"chip-on":"chip-off"}`} onClick={()=>setActiveFamily(label)}>
                            {label} <span style={{ opacity:0.5 }}>{count}</span>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                  <div style={{ height:1,background:T.border,marginBottom:12 }}/>
                </>
              )}

              {!loading && (
                <div style={{ display:"flex",flexDirection:"column",gap:8 }}>
                  {displayed.map((item,i)=><ResultCard key={`${item.id||i}-${i}`} item={item} index={i}/>)}
                </div>
              )}

              {!loading && !error && results.length===0 && (
                <div style={{ textAlign:"center",padding:"60px 0",animation:"fadeIn 0.4s ease" }}>
                  <div style={{ fontSize:24,color:T.grey5,marginBottom:10 }}>◎</div>
                  <div style={{ color:T.grey4,fontFamily:"'JetBrains Mono',monospace",fontSize:12,letterSpacing:"0.1em" }}>
                    NO RESULTS FOR "{query.toUpperCase()}"
                  </div>
                  <div style={{ color:T.grey5,fontSize:11,marginTop:6 }}>Try broader keywords</div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </>
  );
}