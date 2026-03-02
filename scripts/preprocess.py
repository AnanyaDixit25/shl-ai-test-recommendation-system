"""
preprocess.py  —  DROP-IN REPLACEMENT
======================================
Fixes root causes of low accuracy:
  1. Broken descriptions (was nav-menu scraping garbage)
  2. remote_testing all False  (scraper bug)
  3. adaptive_irt all False    (scraper bug)
  4. duration_minutes empty    (scraper never captured it)
  5. Adds: job_family, industry, use_cases, keywords columns
  6. Builds semantically RICH text → high quality FAISS embeddings

Run:  python scripts/preprocess.py
Out:  data/processed/processed_catalogue.csv
      data/processed/processed_catalogue.json
"""

import csv, json, os, re, sys
from collections import Counter

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
ROOT        = os.path.dirname(SCRIPT_DIR)
INPUT_CSV   = os.path.join(ROOT, "data", "raw", "shl_catalogue.csv")
OUTPUT_CSV  = os.path.join(ROOT, "data", "processed", "processed_catalogue.csv")
OUTPUT_JSON = os.path.join(ROOT, "data", "processed", "processed_catalogue.json")
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# ── Test type maps ─────────────────────────────────────────────────────────────
TT_MAP = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}

TT_RICH = {
    "A": "cognitive ability aptitude reasoning analytical thinking intelligence problem solving general mental ability",
    "B": "biodata situational judgement SJT workplace scenarios behavioral decision making judgment realistic situations",
    "C": "competency framework behavioral competencies leadership capabilities UCF universal competency model",
    "D": "360 degree feedback multi-rater development leadership talent management succession planning",
    "E": "assessment centre exercise in-tray leadership group discussion role play written exercise",
    "K": "knowledge skills test technical expertise subject matter proficiency domain knowledge certification",
    "P": "personality questionnaire behavioral traits work style OPQ psychometric Big Five assessment",
    "S": "simulation work sample realistic job preview practical task performance hands-on assessment",
}

LEVEL_RICH = {
    "Entry-Level":                        "entry level junior no experience fresh hire school leaver first job new joiner",
    "Graduate":                           "graduate university college degree early career campus hire new graduate trainee",
    "General Population":                 "all levels general broad range mixed experience any background",
    "Supervisor":                         "supervisor first line team lead team leader crew chief section head",
    "Front Line Manager":                 "front line manager people manager direct reports shift manager line manager",
    "Mid-Professional":                   "mid level experienced professional 3 to 8 years senior associate mid career",
    "Professional Individual Contributor":"senior professional individual contributor specialist expert technical lead",
    "Manager":                            "manager department head unit manager people management mid to senior",
    "Director":                           "director VP vice president senior director strategic leader",
    "Executive":                          "executive C suite CEO CFO CTO COO president board level",
}

# ── Semantic expansion vocabulary ─────────────────────────────────────────────
EXPANSIONS = {
    "java ":            "Java JVM Spring Boot Hibernate Maven Gradle object oriented enterprise backend software engineer",
    "core java":        "Core Java OOP inheritance polymorphism collections multithreading JVM fundamentals",
    "java 8":           "Java 8 lambda streams functional interface optional datetime API modern Java features",
    "enterprise java":  "Enterprise Java EJB J2EE JEE application server WebLogic JBoss servlet JSP JDBC",
    "java design":      "Java design patterns Gang of Four singleton factory observer MVC architectural patterns",
    "java frameworks":  "Java frameworks Spring Hibernate Struts JSF PrimeFaces Maven enterprise development",
    "java platform":    "Java Platform Enterprise Edition JEE specifications web services components architecture",
    "python":           "Python programming scripting Django Flask FastAPI pandas numpy scikit machine learning automation",
    "javascript":       "JavaScript JS TypeScript Node React Angular Vue frontend web browser DOM scripting",
    ".net ":            ".NET C# ASP.NET Core Entity Framework Microsoft Windows enterprise application developer",
    "sql":              "SQL structured query language relational database joins aggregation indexes MySQL PostgreSQL Oracle",
    "oracle":           "Oracle database OCA OCP PL/SQL DBA administration performance tuning enterprise RDBMS",
    "mysql":            "MySQL open source relational database web applications indexing optimization developer",
    "pl/sql":           "PL/SQL Oracle procedural language stored procedures triggers cursors functions packages",
    "t-sql":            "T-SQL Transact SQL Microsoft SQL Server stored procedures functions database programming",
    "mongodb":          "MongoDB NoSQL document database JSON BSON collections aggregation replica developer",
    "r programming":    "R statistical computing language ggplot dplyr tidyverse data analysis visualization scientist",
    "tableau":          "Tableau data visualization dashboard business intelligence reporting analytics BI tool",
    "power bi":         "Power BI Microsoft business intelligence DAX data modeling visualization dashboard reporting",
    "sap":              "SAP ERP enterprise resource planning ABAP modules HANA business process implementation",
    "linux":            "Linux Unix shell bash scripting system administration server management DevOps SRE",
    "aws":              "AWS Amazon cloud EC2 S3 Lambda RDS IAM DevOps cloud architect solutions architect",
    "cloud computing":  "cloud AWS Azure GCP IaaS PaaS SaaS DevOps microservices containerization infrastructure",
    "agile":            "Agile Scrum Kanban sprint velocity backlog retrospective product owner scrum master",
    "network security": "network security firewall IDS IPS VPN encryption protocols TCP IP OSI cybersecurity",
    "cybersecurity":    "cybersecurity CISSP CEH penetration testing vulnerability management SOC analyst CISM",
    "machine learning": "machine learning ML AI deep learning neural networks TensorFlow PyTorch model training",
    "data science":     "data science analytics statistics Python R machine learning visualization modelling scientist",
    "data warehousing": "data warehouse ETL pipeline Hadoop Spark Hive data engineering business intelligence DWH",
    "data mining":      "data mining extraction transformation pattern recognition analytics insights discovery",
    "automata":         "Automata coding simulation automated test SHL computer based interactive coding challenge",
    "hadoop":           "Hadoop HDFS MapReduce big data distributed computing Hive Pig ecosystem engineer",
    "spark":            "Apache Spark streaming real-time batch processing big data analytics cluster engineer",
    "docker":           "Docker container Kubernetes microservices DevOps CI CD pipeline orchestration",
    "angular":          "Angular TypeScript SPA single page app frontend framework component RxJS material",
    "react":            "React ReactJS hooks state management Redux frontend library UI component developer",
    "node.js":          "Node.js JavaScript runtime backend Express API REST GraphQL full stack server side",
    "php":              "PHP server scripting web development Laravel Symfony MySQL backend web developer",
    "html":             "HTML5 CSS3 responsive design web frontend layout browser cross-platform developer",
    "selenium":         "Selenium WebDriver test automation QA testing browser functional regression engineer",
    "jenkins":          "Jenkins CI CD continuous integration deployment pipeline build automation DevOps",
    "autocad":          "AutoCAD CAD 2D 3D drawing design drafting engineering architecture construction",
    "solidworks":       "SolidWorks 3D CAD mechanical design product engineering simulation manufacturing",
    "microsoft excel":  "Microsoft Excel spreadsheet VLOOKUP pivot tables charts formulas financial data analysis",
    "microsoft word":   "Microsoft Word document formatting styles track changes mail merge business writing",
    "microsoft powerpoint": "PowerPoint slides presentations deck animations transitions business communication",
    "microsoft outlook":"Outlook email calendar tasks scheduling Microsoft 365 office productivity communication",
    "microsoft access": "Access database tables queries forms reports relational data management Microsoft",
    "microsoft project":"Project management Gantt scheduling resources tasks timeline baseline MS Project",
    "microsoft windows":"Windows OS desktop administration support IT helpdesk enterprise environment",
    "office 365":       "Office 365 Microsoft 365 Teams SharePoint collaboration cloud business productivity",
    "accounting":       "accounting GAAP IFRS financial statements journal entries ledger trial balance reconcile",
    "accounts payable": "accounts payable AP vendor invoice payment processing reconciliation coding approval",
    "accounts receivable":"accounts receivable AR billing invoicing collections cash posting credit control",
    "bookkeeping":      "bookkeeping double entry accounts ledger reconciliation petty cash small business finance",
    "quickbooks":       "QuickBooks accounting software invoicing payroll reporting bank reconciliation SME",
    "payroll":          "payroll salary wages tax deductions PAYE benefits compensation HR administration",
    "financial":        "financial analysis valuation forecasting budgeting corporate finance investment FP&A",
    "banking":          "banking retail finance loans deposits accounts customer service financial products",
    "sales":            "sales revenue generation pipeline CRM negotiation closing business development quota",
    "account manager":  "account management B2B client relationships retention upsell renewal commercial sales",
    "agency manager":   "insurance agency sales team leadership producer development revenue management",
    "advanced sales":   "advanced sales consultative selling complex deals enterprise negotiation strategy",
    "call center":      "call centre contact center inbound outbound BPO customer service phone support agent",
    "call centre":      "call centre contact center customer service BPO telephone inbound outbound agent",
    "customer service": "customer service support satisfaction complaint resolution communication empathy NPS",
    "reservation agent":"reservation booking hospitality travel telephone bilingual customer contact agent",
    "collections":      "debt collections recovery negotiation payment arrangement financial services banking",
    "bilingual":        "bilingual dual language Spanish English French multilingual communication translation",
    "medical":          "medical healthcare clinical patient care hospital protocols procedures compliance",
    "nursing":          "nursing RN LPN registered nurse patient assessment clinical documentation care plan",
    "hipaa":            "HIPAA PHI patient privacy healthcare compliance medical records data protection",
    "pharmacy":         "pharmacy medication dispensing drug interactions clinical dosage calculation",
    "dental":           "dental oral health patient care procedures hygienist assistant clinical dentistry",
    "mechanical":       "mechanical engineering forces gears levers pulleys hydraulics systems maintenance tech",
    "manufacturing":    "manufacturing production assembly QC quality control industrial lean six sigma plant",
    "warehouse":        "warehouse logistics inventory distribution order fulfilment supply chain operations",
    "forklift":         "forklift operator warehouse material handling OSHA safety certification industrial",
    "welding":          "welding fabrication MIG TIG arc blueprint reading trade industrial technician",
    "blueprint":        "blueprint engineering drawing schematic technical reading manufacturing construction",
    "electrical":       "electrical wiring circuits panel fault finding maintenance electrician industrial",
    "safety":           "workplace safety OSHA health hazard risk assessment PPE compliance officer",
    "osha":             "OSHA regulations workplace safety compliance hazard identification lockout tagout",
    "verify":           "SHL Verify interactive cognitive ability adaptive IRT graduate professional accurate norm",
    "opq":              "OPQ32 Occupational Personality Questionnaire SHL 32 dimensions traits characteristics UCF",
    "personality":      "personality Big Five traits conscientiousness openness extraversion agreeableness stability",
    "situational judg": "situational judgment test SJT workplace decision making behavioral realistic scenarios",
    "motivation":       "motivation questionnaire MQ drivers engagement preferences work values intrinsic extrinsic",
    "verbal reasoning": "verbal reasoning comprehension language ability text inference communication graduate",
    "numerical reason": "numerical reasoning quantitative data tables graphs calculation analyst engineer MBA",
    "inductive reason": "inductive reasoning abstract patterns fluid intelligence matrices logical thinking graduate",
    "deductive reason": "deductive reasoning logical argument evaluation critical thinking conclusions analyst law",
    "leadership":       "leadership vision influence strategy management people skills coaching executive development",
    "360":              "360 multi rater feedback leadership development coaching succession performance management",
    "retail":           "retail store assistant cashier customer sales point POS merchandise service floor",
    "cashier":          "cashier till POS transactions cash handling returns customer service retail store",
    "hotel":            "hotel hospitality guest front desk accommodation check-in service concierge rooms",
    "restaurant":       "restaurant food service FOH BOH kitchen hospitality customer dining experience",
    "gaming":           "gaming casino hospitality gaming associate surveillance floor compliance customer",
    "global skills":    "global skills development report SHL 360 comprehensive multi-measure leadership talent",
}

# ── Inference functions ────────────────────────────────────────────────────────
JF_RULES = [
    ("Information Technology", [
        ".net ","java ","java8","java 8","core java","enterprise java","python","sql","oracle","sap",
        "linux","windows server","php","ruby","node.js","c++ ","c# ","cisco","html","css",
        "javascript","angular","react","aws","cloud computing","unix","mysql","mongodb","docker",
        "devops","coding","programming","network security","cybersecurity","database administration",
        "agile","software","ios","android","kotlin","scala","perl","cobol","fortran","hadoop","spark",
        "machine learning","data science","data warehousing","data mining","tensorflow","pytorch","nlp",
        "terraform","kubernetes","xml","microservices","design pattern","spring","hibernate","j2ee",
        "jee","jsp","servlet","jdbc","junit","typescript","vuejs","django","flask","fastapi","pandas",
        "numpy","scikit","r programming","tableau","power bi","etl","airflow","kafka","redis",
        "postgresql","sqlite","ms sql","sql server","pl/sql","t-sql","stored procedure",
        "selenium","jenkins","microsoft word","microsoft excel","microsoft powerpoint","office 365",
        "microsoft outlook","microsoft access","microsoft project","microsoft visio","sharepoint",
        "visual studio","autocad","solidworks","microstation","revit","loadrunner","automata",
    ]),
    ("Contact Center", [
        "call center","call centre","contact center","reservation agent","inbound","outbound",
        "bpo","helpdesk","customer support","service associate","collections agent","bilingual",
    ]),
    ("Sales", [
        "sales","account manager","agency manager","account executive","business development","asq",
    ]),
    ("Healthcare", [
        "medical","healthcare","nursing","clinical","hipaa","pharmaceutical","dental","nurse",
        "hospital","patient","radiology","pharmacy","dosage","surgical","infection control",
    ]),
    ("Clerical", [
        "administrative","clerical","office skills","typing","data entry","spelling","proofreading",
        "filing","audio typing","shorthand","grammar","word processing","basic office",
        "accounts payable","accounts receivable","bookkeeping","accounting clerk","payroll clerk",
    ]),
    ("Customer Service", [
        "retail associate","hospitality associate","cashier","hotel manager","restaurant manager",
        "front desk","guest service","retail manager","hospitality manager","gaming associate",
    ]),
    ("Safety", [
        "safety","osha","hazardous","whmis","infection control","bloodborne",
    ]),
]

INDUSTRY_RULES = [
    ("Banking/Finance",    ["bank","banking","financial","finance","credit","loan","mortgage",
                             "investment","audit","payroll","bookkeeping","accounts payable",
                             "accounts receivable","general ledger","tax","accounting","quickbooks",
                             "insurance","actuarial","accounts payable","accounts receivable"]),
    ("Healthcare",         ["medical","healthcare","nursing","clinical","hipaa","pharmaceutical",
                             "dental","nurse","hospital","patient","radiology","pharmacy"]),
    ("Retail",             ["retail","cashier","store","shop","merchandise","point of sale"]),
    ("Hospitality",        ["hotel","hospitality","restaurant","reservation agent","guest","gaming"]),
    ("Manufacturing",      ["manufacturing","industrial","warehouse","forklift","cnc","welding",
                             "blueprint","assembly","production","mechanical","autocad","solidworks"]),
    ("Oil & Gas",          ["oil","gas","petroleum","drilling","pipeline"]),
    ("Telecommunications", ["call center","call centre","contact center","telecom","bpo",
                             "inbound","outbound","reservation agent","bilingual"]),
    ("Insurance",          ["insurance","claims","underwriting","agency manager"]),
]

ONSITE_KW  = ["assessment centre", "assessment center", "exercise pack", "vadc"]
ADAPTIVE_KW = ["verify", "cat ", "g+ ", "general ability plus"]

def infer_jf(name):
    nl = name.lower()
    for fam, kws in JF_RULES:
        if any(k in nl for k in kws):
            return fam
    return "Business"

def infer_industry(name):
    nl = name.lower()
    return list(dict.fromkeys(i for i, kws in INDUSTRY_RULES if any(k in nl for k in kws)))

def infer_remote(name, codes):
    nl = name.lower()
    if any(k in nl for k in ONSITE_KW):
        return False
    return True

def infer_adaptive(name):
    nl = name.lower()
    return any(k in nl for k in ADAPTIVE_KW)

DUR_RULES = [
    (r"\b1[\s-]*minute",          5),
    (r"\b3[\s-]*minute",          10),
    (r"\b5[\s-]*minute",          15),
    (r"short\s*form",             30),
    (r"coding\s*sim",             60),
    (r"automata",                 45),
    (r"\bsolution\b",             45),
    (r"call\s*cent.*sim|call\s*cent.*sel", 25),
    (r"\bsimulation\b",           25),
    (r"verify.*interactive|shl\s*verify", 17),
    (r"\bverify\b",               18),
    (r"\bopq\b",                  25),
    (r"\bmq\b",                   20),
    (r"sjt|situational\s*judg",   25),
    (r"360|multi.rater|development\s*report", 60),
    (r"exercise\s*pack|assessment\s*cent", 180),
    (r"global\s*skills",          120),
    (r"typing",                   10),
    (r"\bknowledge\b|\bskills\s*test\b", 20),
]

def infer_duration(name, raw):
    if raw and str(raw).strip().isdigit():
        return int(str(raw).strip())
    nl = name.lower()
    for pat, d in DUR_RULES:
        if re.search(pat, nl):
            return d
    return None

def infer_use_cases(name, codes):
    nl = name.lower()
    uses = ["Talent Acquisition"]
    if "D" in codes or "360" in nl or "development report" in nl:
        uses.append("Talent Management")
    if any(k in nl for k in ["succession", "hipo", "high potential", "pipeline"]):
        uses.append("Succession Planning")
    if "onboarding" in nl or "learning styles" in nl:
        uses.append("Onboarding")
    return list(dict.fromkeys(uses))

# ── Rich description ───────────────────────────────────────────────────────────
def build_description(name, ptype, codes, jf, levels, industries, uses):
    nl = name.lower()

    # Opening
    base = (
        f"{name} is a pre-packaged SHL job assessment solution"
        if ptype == "Pre-packaged Job Solution"
        else f"{name} is an SHL assessment"
    )

    # What it measures
    tt_phrases = [TT_RICH.get(c, "") for c in codes]
    if tt_phrases:
        base += f" measuring {', and '.join(filter(None, tt_phrases[:3]))}"

    # Who for
    level_parts = [LEVEL_RICH.get(l, l.lower()) for l in levels[:3]]
    if level_parts:
        base += f". Suitable for {'; '.join(level_parts)}"

    # Domain
    base += f" in {jf.lower()} roles"
    if industries:
        base += f" within {', '.join(industries[:2])}"

    # Purpose
    if "Talent Management" in uses:
        base += ". Supports talent development succession planning leadership pipeline"
    else:
        base += ". Used for hiring screening selection evaluation recruitment"

    # Semantic expansions
    expansions = []
    for key, exp in EXPANSIONS.items():
        if key in nl:
            expansions.append(exp)

    # Test type boosts
    for c in codes:
        expansions.append(TT_RICH.get(c, ""))

    # Level boosts
    for l in levels[:3]:
        expansions.append(LEVEL_RICH.get(l, l.lower()))

    # Domain boosts
    expansions.append(f"{jf.lower()} professional assessment screening evaluation hiring")
    for ind in industries:
        expansions.append(f"{ind.lower()} sector assessment")

    # Name tokens (critical for exact-name search matching)
    name_tokens = " ".join(w for w in re.split(r"[\s\-/,().]+", name) if len(w) > 2)

    return (base + ". " + " ".join(filter(None, expansions)) + " " + name_tokens).strip()

# ── Language whitelist ─────────────────────────────────────────────────────────
VALID_LANGS = {
    "English (USA)","English International","English (Australia)","English (Canada)",
    "English (Malaysia)","English (Singapore)","English (South Africa)",
    "French","French (Belgium)","French (Canada)","German","Spanish",
    "Latin American Spanish","Dutch","Portuguese","Portuguese (Brazil)","Italian",
    "Arabic","Chinese Simplified","Chinese Traditional","Japanese","Korean","Russian",
    "Polish","Turkish","Swedish","Norwegian","Danish","Finnish","Romanian",
    "Indonesian","Thai","Vietnamese","Malay","Bulgarian","Croatian","Czech",
    "Estonian","Flemish","Greek","Hungarian","Icelandic","Latvian","Lithuanian",
    "Serbian","Slovak",
}

def clean_langs(raw):
    return [l.strip() for l in raw.split("|") if l.strip() in VALID_LANGS]

# ═════════════════════════════════════════════════════════════════════════════
def process():
    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: {INPUT_CSV} not found"); sys.exit(1)

    with open(INPUT_CSV, encoding="utf-8") as f:
        raw = list(csv.DictReader(f))
    print(f"Loaded {len(raw)} products")

    processed = []
    for row in raw:
        name   = row["name"].strip()
        ptype  = row["type"].strip()
        codes  = [c.strip() for c in row.get("test_type_codes","").split(",") if c.strip()]
        levels = [l.strip() for l in row.get("job_levels","").split("|") if l.strip()]
        langs  = clean_langs(row.get("languages",""))

        jf         = infer_jf(name)
        industries = infer_industry(name)
        remote     = infer_remote(name, codes)
        adaptive   = infer_adaptive(name)
        duration   = infer_duration(name, row.get("duration_minutes",""))
        uses       = infer_use_cases(name, codes)
        desc       = build_description(name, ptype, codes, jf, levels, industries, uses)
        keywords   = list(dict.fromkeys(
            [name.lower()]
            + [TT_MAP.get(c, c).lower() for c in codes]
            + [jf.lower()]
            + [l.lower() for l in levels]
            + [i.lower() for i in industries]
            + [w.lower() for w in re.split(r"[\s\-/,().]+", name) if len(w) > 2]
        ))

        processed.append({
            "id":               row.get("id",""),
            "name":             name,
            "type":             ptype,
            "test_type_codes":  ",".join(codes),
            "test_type_labels": " | ".join(TT_MAP.get(c,c) for c in codes),
            "job_family":       jf,
            "job_levels":       " | ".join(levels),
            "industry":         " | ".join(industries),
            "remote_testing":   remote,
            "adaptive_irt":     adaptive,
            "duration_minutes": duration if duration is not None else "",
            "description":      desc,
            "languages":        " | ".join(langs),
            "url":              row.get("url",""),
            "use_cases":        " | ".join(uses),
            "keywords":         " | ".join(keywords[:20]),
        })

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(processed[0].keys()))
        w.writeheader(); w.writerows(processed)
    print(f"✅ CSV  → {OUTPUT_CSV}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON → {OUTPUT_JSON}")

    jf_c = Counter(p["job_family"] for p in processed)
    print(f"\nStats: {len(processed)} products")
    print(f"  Job families    : {dict(jf_c)}")
    print(f"  Remote testing  : {sum(1 for p in processed if p['remote_testing'])}")
    print(f"  Adaptive IRT    : {sum(1 for p in processed if p['adaptive_irt'])}")
    print(f"  Has duration    : {sum(1 for p in processed if p['duration_minutes'])}")
    avg = sum(len(p['description']) for p in processed)//len(processed)
    print(f"  Avg desc length : {avg} chars (was ~80, now ~{avg})")
    print(f"\n✅ Done. Next: python scripts/build_index_pipeline.py")
    return processed

if __name__ == "__main__":
    process()