"""
build_final_db.py  
==================
Comprehensive extractor producing the final motor_vehicles_db_final.json
Strategy:
  - Chapters 1,2,3,4,6,7: em-dash (U+2014) boundary detection  
  - Chapter 5:  broader dash pattern (em/en/hyphen-dash) since it 
                contains many specification rules with table content
  - Appendices: named-section + sub-rule approach
  - MVA 1988:   IndiaKanoon scraping with retry logic

Run: python build_final_db.py
Output: data/motor_vehicles_db_final.json  (also copied to workspace)
"""

import os, re, json, time
import requests
from pypdf import PdfReader

# ── Config ───────────────────────────────────────────────────────────────────
DATA_DIR    = "data/cmvr_pdfs"
OUTPUT_FILE = "data/motor_vehicles_db_final.json"
WORKSPACE   = r"D:\moptor_vehical_dataset\motor_vehicles_db.json"

EMDASH = "\u2014"
ENDASH = "\u2013"

CHAPTER_META = {
    "CMVR-chapter1_1.pdf": {"number": 1, "name": "Preliminary"},
    "CMVR-chapter2_1.pdf": {"number": 2, "name": "Licensing of Drivers of Motor Vehicles"},
    "CMVR-chapter3_1.pdf": {"number": 3, "name": "Registration of Motor Vehicles"},
    "CMVR-chapter4_1.pdf": {"number": 4, "name": "Control of Transport Vehicles"},
    "CMVR-chapter5_1.pdf": {"number": 5, "name": "Construction, Equipment and Maintenance"},
    "CMVR-chapter6_1.pdf": {"number": 6, "name": "Special Provisions: State Transport Undertakings"},
    "CMVR-chapter7_1.pdf": {"number": 7, "name": "Insurance Against Third Party Risks"},
    "Appendices__1.pdf":   {"number": 0, "name": "Appendices, Orders and Regulations"},
}

LEGAL_KEYWORDS = [
    "driving licence","registration","permit","insurance","transport","motor vehicle",
    "highway","speed","accident","penalty","offence","certificate","authority",
    "licence","fitness","emission","fuel","conductor","driver","owner","vehicle",
    "road","traffic","tax","weight","dimension","brake","horn","signal",
    "overtaking","parking","towing","goods","passenger","tourist","bus","truck",
    "motorcycle","ambulance","fire","police","court","fine","imprisonment",
    "construction","equipment","maintenance","silencer","headlamp","tyre",
    "wheel","axle","body","engine","steering","seat","windscreen","mirror",
]

MVA_CHAPTERS = [
    {"number": 1,  "title": "Preliminary",                                         "section_range": (1,   2)},
    {"number": 2,  "title": "Licensing of Drivers of Motor Vehicles",              "section_range": (3,  26)},
    {"number": 3,  "title": "Licensing of Conductors of Stage Carriages",          "section_range": (27, 38)},
    {"number": 4,  "title": "Registration of Motor Vehicles",                      "section_range": (39, 64)},
    {"number": 5,  "title": "Control of Transport Vehicles",                       "section_range": (65, 96)},
    {"number": 6,  "title": "Special Provisions: State Transport Undertakings",    "section_range": (97,103)},
    {"number": 7,  "title": "Construction, Equipment and Maintenance",             "section_range":(104,116)},
    {"number": 8,  "title": "Control of Traffic",                                  "section_range":(117,141)},
    {"number": 9,  "title": "Motor Vehicles Temporarily Leaving India",            "section_range":(142,147)},
    {"number": 10, "title": "Liability Without Fault in Certain Cases",            "section_range":(148,150)},
    {"number": 11, "title": "Insurance Against Third Party Risks",                 "section_range":(145,164)},
    {"number": 12, "title": "Claims Tribunals",                                    "section_range":(165,176)},
    {"number": 13, "title": "Offences, Penalties and Procedure",                  "section_range":(177,210)},
    {"number": 14, "title": "Miscellaneous",                                       "section_range":(211,217)},
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def pdf_to_text(path):
    try:
        reader = PdfReader(path)
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts)
    except Exception as e:
        print(f"  ERROR reading PDF: {e}")
        return ""

def clean_text(text):
    lines = text.split("\n")
    out = []
    for line in lines:
        s = line.strip()
        if re.match(r"^\d{1,3}$", s):
            continue
        if "Central Motor Vehicles Rules" in s and len(s) < 70:
            continue
        if re.match(r"^CHAPTER\s+[IVXLC]+\s*$", s):
            continue
        out.append(line)
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(\w)-\n\s*(\w)", r"\1\2", text)
    return text

def get_keywords(text):
    tl = text.lower()
    return sorted({kw for kw in LEGAL_KEYWORDS if kw in tl})

def count_sub_rules(text):
    return len(re.findall(r"\(\d+\)", text)) + len(re.findall(r"\([a-z]\)", text))

def build_rule(num, title, content, chapter_meta, fname, rule_type="rule"):
    content = re.sub(r"[ \t]{2,}", " ", content).strip()
    return {
        "rule_number":     num,
        "rule_title":      title.strip().rstrip(".").strip(),
        "chapter_number":  chapter_meta["number"],
        "chapter_name":    chapter_meta["name"],
        "source_file":     fname,
        "rule_type":       rule_type,
        "content":         content,
        "keywords":        get_keywords(content),
        "sub_rules_count": count_sub_rules(content),
    }

# ── CMVR Chapter extractor ────────────────────────────────────────────────────
# Standard pattern: "N.  Title.—"  (em-dash)
RULE_EM = re.compile(
    r"(?:^|\n)\s*(\d{1,3})\.\s+([^\n]{3,100}?)\u2014",
    re.MULTILINE
)

# Broader pattern for Ch5: allows em/en/regular dash and period
RULE_BROAD = re.compile(
    r"(?:^|\n)\s*(\d{1,3})\.\s+([A-Z][^\n]{3,100}?)[\u2014\u2013\-]\s*(?=\(|\w)",
    re.MULTILINE
)

def extract_chapter(fname, chapter_meta):
    path = os.path.join(DATA_DIR, fname)
    raw  = pdf_to_text(path)
    text = clean_text(raw)

    # Ch5: use broader pattern since it has many spec rules with varied dashes
    if chapter_meta["number"] == 5:
        matches = list(RULE_BROAD.finditer(text))
        # Fallback to em-dash only if broader finds too many false positives
        em_matches = list(RULE_EM.finditer(text))
        if len(em_matches) > len(matches):
            matches = em_matches
        # Filter: rule numbers for Ch5 should be 91+
        matches = [m for m in matches if int(m.group(1)) >= 91]
    else:
        matches = list(RULE_EM.finditer(text))

    rules = []
    for i, m in enumerate(matches):
        num   = int(m.group(1))
        title = m.group(2)
        start = m.start()
        end   = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end]
        rules.append(build_rule(num, title, content, chapter_meta, fname))

    # Deduplicate by rule_number (keep first occurrence)
    seen = set()
    deduped = []
    for r in rules:
        key = r["rule_number"]
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped

# ── Appendix extractor ────────────────────────────────────────────────────────
APP_SECTION_HEAD = re.compile(
    r"(?:^|\n)((?:APPENDIX\s+[IVXLCM]+|THE\s+MOTOR\s+VEHICLES[^\n]{0,80}|"
    r"RULES\s+OF\s+THE\s+ROAD[^\n]{0,40}|SOLATIUM\s+SCHEME[^\n]{0,40}|"
    r"RENT\s+A\s+(?:CAB|MOTOR\s+CYCLE)[^\n]{0,40}|"
    r"NATIONAL\s+PERMIT[^\n]{0,40}|THE\s+LIQUEFIED[^\n]{0,40}|"
    r"HIGH\s+SECURITY\s+REGISTRATION[^\n]{0,40}|"
    r"BUS\s+BODY\s+BUILDER[^\n]{0,40}|DRIVING\s+LICENCE[^\n]{0,40}))\s*\n",
    re.MULTILINE | re.IGNORECASE
)

def extract_appendix(fname, chapter_meta):
    path   = os.path.join(DATA_DIR, fname)
    raw    = pdf_to_text(path)
    text   = clean_text(raw)
    rules  = []
    secs   = list(APP_SECTION_HEAD.finditer(text))

    for i, sec in enumerate(secs):
        sec_title = sec.group(1).strip()
        sec_start = sec.start()
        sec_end   = secs[i+1].start() if i+1 < len(secs) else len(text)
        sec_text  = text[sec_start:sec_end]

        sub_matches = list(RULE_EM.finditer(sec_text))
        if sub_matches:
            for j, sm in enumerate(sub_matches):
                num   = int(sm.group(1))
                title = sm.group(2)
                s     = sm.start()
                e     = sub_matches[j+1].start() if j+1 < len(sub_matches) else len(sec_text)
                content = sec_text[s:e]
                r = build_rule(num, title, content, chapter_meta, fname)
                r["appendix_section"] = sec_title
                rules.append(r)
        else:
            content = re.sub(r"[ \t]{2,}", " ", sec_text).strip()
            rules.append({
                "rule_number":      f"App-{i+1}",
                "rule_title":       sec_title,
                "chapter_number":   0,
                "chapter_name":     chapter_meta["name"],
                "appendix_section": sec_title,
                "source_file":      fname,
                "rule_type":        "appendix_section",
                "content":          content,
                "keywords":         get_keywords(content),
                "sub_rules_count":  count_sub_rules(content),
            })
    return rules

# ── MVA 1988 scraper ─────────────────────────────────────────────────────────
MVA_BASE = "https://indiankanoon.org"

def scrape_mva():
    print("\n[2/2] Scraping Motor Vehicles Act 1988 from IndiaKanoon...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"}

    # Known IndiaKanoon doc IDs for MV Act sections
    # These are the correct search URLs for IndiaKanoon
    search_urls = [
        "/search/?formInput=Motor+Vehicles+Act+section+doctype%3Alegislation&pagenum=0",
        "/search/?formInput=Motor+Vehicles+Act+1988&pagenum=0",
    ]

    act_page = None
    for surl in search_urls:
        try:
            r = requests.get(MVA_BASE + surl, headers=headers, timeout=20)
            # Look for MV Act link in results
            doc_links = re.findall(
                r'href="(/doc/\d+/)"[^>]*>([^<]*Motor Vehicles Act[^<]*)',
                r.text, re.IGNORECASE
            )
            if doc_links:
                act_path, act_name = doc_links[0]
                print(f"  Found: {act_name.strip()} at {act_path}")
                act_page = requests.get(MVA_BASE + act_path, headers=headers, timeout=30).text
                break
        except Exception as e:
            print(f"  Search error: {e}")

    # Try direct known URL
    if not act_page:
        known_ids = ["1362234", "1643074"]
        for doc_id in known_ids:
            try:
                url = f"{MVA_BASE}/doc/{doc_id}/"
                print(f"  Trying direct: {url}")
                r = requests.get(url, headers=headers, timeout=20)
                if "Motor Vehicles" in r.text and r.status_code == 200:
                    act_page = r.text
                    print(f"  Got page ({len(act_page)} chars)")
                    break
            except Exception as e:
                print(f"  Error: {e}")

    if not act_page:
        print("  Could not reach IndiaKanoon for MVA.")
        return []

    # Extract section links from the act page
    # IndiaKanoon format: anchor tags with section numbers
    sec_pattern = re.compile(
        r'href="(/doc/(\d+)/)"[^>]*>\s*(?:Section\s+)?(\d+)\b',
        re.IGNORECASE
    )
    found = {}
    for m in sec_pattern.finditer(act_page):
        doc_path = m.group(1)
        sec_num  = int(m.group(3))
        if 1 <= sec_num <= 217 and sec_num not in found:
            found[sec_num] = doc_path

    section_links = sorted(found.items())
    print(f"  Found {len(section_links)} section links")

    if not section_links:
        print("  No section links found. Structure may have changed.")
        return []

    sections = []
    for sec_num, doc_path in section_links:
        url = MVA_BASE + doc_path
        try:
            sr  = requests.get(url, headers=headers, timeout=15)
            html = sr.text
            # Extract text content
            text_m = re.search(r'<pre[^>]*>(.*?)</pre>', html, re.DOTALL)
            if not text_m:
                text_m = re.search(r'class="judgments"[^>]*>(.*?)</div>', html, re.DOTALL)
            if text_m:
                raw = re.sub(r'<[^>]+>', ' ', text_m.group(1))
                raw = re.sub(r'\s{2,}', ' ', raw).strip()
            else:
                # Try to grab body text
                body = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
                raw = re.sub(r'<[^>]+>', ' ', body.group(1)) if body else ""
                raw = re.sub(r'\s{2,}', ' ', raw).strip()[:2000]

            title_m = re.match(r'(?:Section\s+)?\d+\.?\s+([^.\n]{3,80})', raw)
            title = title_m.group(1).strip() if title_m else f"Section {sec_num}"

            sections.append({
                "section_number": sec_num,
                "section_title":  title,
                "content":        raw,
                "source_url":     url,
                "keywords":       get_keywords(raw),
            })
            print(f"  Section {sec_num:3d}: {title[:40]:40s} ({len(raw)} chars)")
            time.sleep(0.8)
        except Exception as e:
            print(f"  Error section {sec_num}: {e}")

    return sections

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("MOTOR VEHICLES DB — FINAL BUILD")
    print("=" * 65)

    # ── 1. CMVR ───────────────────────────────────────────────────────────
    print("\n[1/2] Extracting CMVR 1989 rules from PDFs...")
    all_rules = []
    ch_summary = {}

    for fname in sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".pdf")):
        meta = CHAPTER_META.get(fname, {"number": -1, "name": "Unknown"})
        print(f"\n  {fname} → Ch.{meta['number']}: {meta['name']}")

        if fname == "Appendices__1.pdf":
            rules = extract_appendix(fname, meta)
        else:
            rules = extract_chapter(fname, meta)

        print(f"  → {len(rules)} rules")
        if rules:
            nums = [r["rule_number"] for r in rules if isinstance(r["rule_number"], int)]
            if nums:
                print(f"  → Range: {min(nums)} – {max(nums)}")

        all_rules.extend(rules)
        ch = meta["number"]
        if ch not in ch_summary:
            ch_summary[ch] = {"chapter_number": ch, "chapter_name": meta["name"], "rule_count": 0}
        ch_summary[ch]["rule_count"] += len(rules)

    # Sort
    all_rules.sort(key=lambda r: (
        r.get("chapter_number", 99),
        r["rule_number"] if isinstance(r["rule_number"], int) else 9999,
        str(r["rule_number"])
    ))

    print(f"\n  CMVR TOTAL: {len(all_rules)} rules")

    # ── 2. MVA ────────────────────────────────────────────────────────────
    mva_sections = scrape_mva()
    print(f"  MVA TOTAL: {len(mva_sections)} sections")

    # ── 3. Compile ────────────────────────────────────────────────────────
    db = {
        "metadata": {
            "title":        "Motor Vehicles Act & Rules Database",
            "description":  "Motor Vehicles Act 1988 + Central Motor Vehicles Rules 1989",
            "version":      "3.0",
            "last_updated": "2026-02-19",
            "generated_by": "Motor Vehicles DB Builder v3 (Python)",
            "sources": [
                {"name": "MORTH",       "url": "https://morth.gov.in",          "content": "CMVR 1989 PDFs"},
                {"name": "IndiaKanoon", "url": "https://indiankanoon.org",       "content": "MV Act 1988 sections"},
            ],
            "statistics": {
                "total_cmvr_rules":   len(all_rules),
                "total_mva_sections": len(mva_sections),
                "cmvr_chapters":      7,
                "mva_chapters":       14,
            }
        },
        "acts": [{
            "title":          "Motor Vehicles Act, 1988",
            "short_title":    "MV Act 1988",
            "act_number":     "59 of 1988",
            "year":           1988,
            "ministry":       "Ministry of Road Transport and Highways",
            "total_sections": 217,
            "chapters":       MVA_CHAPTERS,
            "sections":       mva_sections,
            "note":           "" if mva_sections else "Sections unavailable. Provide data/mva_1988.pdf to populate.",
        }],
        "rules": [{
            "title":           "Central Motor Vehicles Rules, 1989",
            "short_title":     "CMVR 1989",
            "year":            1989,
            "notification":    "G.S.R. 590(E), dated 2nd July, 1989",
            "ministry":        "Ministry of Road Transport and Highways",
            "chapter_summary": sorted(ch_summary.values(), key=lambda x: x["chapter_number"]),
            "total_rules":     len(all_rules),
            "rules":           all_rules,
        }],
    }

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024

    # Copy to workspace
    import shutil
    try:
        shutil.copy2(OUTPUT_FILE, WORKSPACE)
        print(f"\n  Copied to workspace: {WORKSPACE}")
    except Exception as e:
        print(f"\n  Could not copy to workspace: {e}")

    print("\n" + "=" * 65)
    print("DONE!")
    print(f"  Output:       {OUTPUT_FILE}  ({size_kb:.1f} KB)")
    print(f"  CMVR rules:   {len(all_rules)}")
    print(f"  MVA sections: {len(mva_sections)}")
    print("\nChapter breakdown (CMVR):")
    for ch in sorted(ch_summary.values(), key=lambda x: x["chapter_number"]):
        print(f"  Ch {ch['chapter_number']:2d} | {ch['chapter_name'][:52]:52s} | {ch['rule_count']:4d} rules")

if __name__ == "__main__":
    main()
