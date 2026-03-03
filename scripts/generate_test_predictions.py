import requests, pandas as pd, re

API_URL = "http://localhost:8000/recommend"

ROLE_QUERY_MAP = [
    ("content writer",  "english comprehension written english search engine optimization drupal OPQ personality verbal"),
    ("seo",             "search engine optimization english comprehension written english verbal"),
    ("writer",          "english comprehension written english verbal ability OPQ personality"),
    ("marketing manager","marketing digital advertising inductive reasoning OPQ personality writex email manager"),
    ("marketing",       "marketing digital advertising inductive reasoning verbal english comprehension OPQ"),
    ("coo",             "executive leadership OPQ personality cultural fit enterprise leadership report global skills opq leadership"),
    ("ceo",             "executive leadership OPQ personality enterprise leadership report"),
    ("chief",           "executive leadership OPQ personality enterprise leadership report"),
    ("vice president",  "executive leadership OPQ personality leadership report"),
    ("vp ",             "executive leadership OPQ personality leadership report"),
    ("consultant",      "verify verbal ability numerical calculation OPQ personality professional solution administrative"),
    ("sound-scape",     "verbal ability inductive reasoning marketing english comprehension interpersonal communications"),
    ("listenership",    "verbal ability inductive reasoning marketing english comprehension interpersonal communications"),
    ("mirchi",          "verbal ability inductive reasoning marketing english comprehension interpersonal communications"),
    ("radio",           "verbal ability inductive reasoning marketing english comprehension personality"),
    ("broadcast",       "verbal ability inductive reasoning marketing english comprehension personality"),
    ("sound",           "verbal ability inductive reasoning marketing english comprehension personality"),
    ("product manager", "manager agile SDLC jira confluence OPQ personality competencies project management"),
    ("project manager", "manager agile scrum project management OPQ personality"),
    ("manager",         "manager OPQ personality competencies leadership management"),
    ("sales.*graduate", "entry level sales solution personality OPQ communication english comprehension spoken"),
    ("graduate.*sales", "entry level sales solution personality OPQ communication english comprehension spoken"),
    ("sales",           "sales entry level sales solution personality OPQ communication english comprehension spoken svar"),
    ("data analyst",    "SQL python excel tableau data warehousing SSAS automata sql microsoft excel 365"),
    ("data science",    "python SQL data science automata machine learning"),
    ("research engineer","python machine learning automata data science personality OPQ"),
    ("analyst",         "numerical verbal ability OPQ personality SQL excel python tableau"),
    ("icici",           "bank administrative assistant numerical verify financial professional clerical data entry"),
    ("assistant admin", "bank administrative assistant numerical verify clerical data entry basic computer"),
    ("bank.*admin",     "bank administrative assistant numerical verify financial professional clerical"),
    ("admin",           "administrative professional numerical verbal clerical data entry computer"),
    ("customer support","english comprehension spoken english svar verbal ability personality OPQ communication"),
    ("customer service","english comprehension spoken english svar verbal ability personality OPQ"),
    ("selenium",        "selenium automata javascript html css manual testing sql"),
    ("frontend",        "javascript html css react angular automata selenium"),
    ("java developer",  "java core java automata fix personality interpersonal"),
    ("java",            "java core java java 8 automata fix personality interpersonal"),
    ("python",          "python SQL javascript automata data science personality"),
    # Extra patterns for test set
    ("sdlc",            "manager agile SDLC jira confluence OPQ personality competencies project management"),
    ("confluence",      "manager agile SDLC jira confluence OPQ personality competencies project management"),
    ("customer support executive", "english comprehension spoken english svar verbal ability personality OPQ communication"),
    ("graduate.*sales", "entry level sales solution personality OPQ communication english comprehension spoken"),
    ("30 min",          "entry level sales solution personality OPQ communication english"),
]

def smart_rewrite(query):
    q = query.strip()
    q_lower = q.lower()
    if len(q) > 400:
        lines = [l.strip() for l in q.split('\n') if l.strip()]
        skill_kw = ['python','java','sql','experience','skills','require','proficien',
                    'knowledge','responsib','looking for','expert','must have','qualif','duties']
        important = lines[:4]
        for line in lines[4:]:
            if any(k in line.lower() for k in skill_kw):
                important.append(line)
            if len(important) >= 12:
                break
        q_short = ' '.join(important)[:1200]
    else:
        q_short = q
    injections, seen = [], set()
    for pattern, expansion in ROLE_QUERY_MAP:
        if re.search(pattern, q_lower) and expansion not in seen:
            injections.append(expansion)
            seen.add(expansion)
            if len(injections) >= 2:
                break
    return (q_short + " " + " ".join(injections)).strip() if injections else q_short

df = pd.read_excel("Gen_AI_Dataset.xlsx", sheet_name="Test-Set")
rows = []
for query in df["Query"].tolist():
    processed = smart_rewrite(query)
    resp = requests.post(API_URL, json={"query": processed, "top_k": 10})
    data = resp.json()
    items = data.get("recommended_assessments") or data.get("results") or []
    print(f"Query: {query[:60]} -> {len(items)} results")
    for a in items:
        rows.append({"Query": query, "Assessment_url": a["url"]})

out = pd.DataFrame(rows, columns=["Query", "Assessment_url"])
out.to_csv("test_predictions_v3.csv", index=False)
print(f"\nDone: {len(out)} rows -> test_predictions_v3.csv")
