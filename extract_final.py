"""
extract_final.py
================
Final robust extractor for:
  1. CMVR 1989 - from downloaded PDFs  (em-dash boundary detection)
  2. MVA  1988 - scraped from indiankanoon.org

Run: python extract_final.py
Output: data/motor_vehicles_db_final.json
"""

import os, re, json, time
import requests
from pypdf import PdfReader

# ── Config ───────────────────────────────────────────────────────────────────
DATA_DIR    = "data/cmvr_pdfs"
OUTPUT_FILE = "data/motor_vehicles_db_final.json"
EMDASH      = "\u2014"

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
]

# ── PDF helpers ───────────────────────────────────────────────────────────────
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
        print(f"  ERROR: {e}")
        return ""

def clean_text(text):
    """Remove running headers, page numbers, normalise whitespace."""
    lines = text.split("\n")
    out = []
    for line in lines:
        s = line.strip()
        # Bare page numbers
        if re.match(r"^\d{1,3}$", s):
            continue
        # Running headers like "Central Motor Vehicles Rules, 1989"
        if "Central Motor Vehicles Rules" in s and len(s) < 70:
            continue
        # Chapter headings
        if re.match(r"^CHAPTER\s+[IVXLC]+\s*$", s):
            continue
        out.append(line)
    text = "\n".join(out)
    # Collapse 3+ blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Fix PDF hyphenation: "mo-\ntor" -> "motor"
    text = re.sub(r"(\w)-\n\s*(\w)", r"\1\2", text)
    return text

# ── CMVR extractor ─────────────────────────────────────────────────────────────
# CMVR rule signature: "N.  Title.—content..."  where — is U+2014
# The rule number appears at START of a line (after optional spaces) followed by period.
RULE_BOUNDARY = re.compile(
    r"(?:^|\n)"                  # start of line
    r"\s*"
    r"(\d{1,3})\."               # rule number
    r"\s+"
    r"([^\n]{3,100}?)"           # title (no newline, 3-100 chars)
    r"\u2014",                   # em-dash — definitive CMVR marker
    re.MULTILINE
)

def get_keywords(text):
    tl = text.lower()
    return sorted({kw for kw in LEGAL_KEYWORDS if kw in tl})

def count_sub_rules(text):
    return len(re.findall(r"\(\d+\)", text)) + len(re.findall(r"\([a-z]\)", text))

def build_rule(num, title, content, chapter_meta, fname):
    content = re.sub(r"[ \t]{2,}", " ", content).strip()
    return {
        "rule_number":    num,
        "rule_title":     title.strip().rstrip("."),
        "chapter_number": chapter_meta["number"],
        "chapter_name":   chapter_meta["name"],
        "source_file":    fname,
        "rule_type":      "rule",
        "content":        content,
        "keywords":       get_keywords(content),
        "sub_rules_count": count_sub_rules(content),
    }

def extract_chapter_rules(fname, chapter_meta):
    path = os.path.join(DATA_DIR, fname)
    raw  = pdf_to_text(path)
    text = clean_text(raw)

    matches = list(RULE_BOUNDARY.finditer(text))
    rules   = []

    for i, m in enumerate(matches):
        num   = int(m.group(1))
        title = m.group(2)
        start   = m.start()
        end     = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end]
        rules.append(build_rule(num, title, content, chapter_meta, fname))

    return rules

# ── Appendix extractor ────────────────────────────────────────────────────────
# Appendices contain named sections (Appendix I, II, Solatium Scheme, etc.)
# Inside each section, sub-rules follow the same N.  Title.— pattern.

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
    path    = os.path.join(DATA_DIR, fname)
    raw     = pdf_to_text(path)
    text    = clean_text(raw)

    # Find named sections
    sections = list(APP_SECTION_HEAD.finditer(text))
    rules    = []

    for i, sec in enumerate(sections):
        sec_title = sec.group(1).strip()
        sec_start = sec.start()
        sec_end   = sections[i+1].start() if i+1 < len(sections) else len(text)
        sec_text  = text[sec_start:sec_end]

        # Try to find sub-rules inside this section
        sub_matches = list(RULE_BOUNDARY.finditer(sec_text))

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
            # Whole section as one entry
            content = sec_text.strip()
            content = re.sub(r"[ \t]{2,}", " ", content)
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
# Motor Vehicles Act 1988 search on IndiaKanoon
MVA_SEARCH = "/search/?formInput=Motor+Vehicles+Act+1988+doctype%3Alegislation&pagenum=0"

MVA_CHAPTERS = [
    {"number": 1,  "title": "Preliminary",                                      "section_range": (1,   2)},
    {"number": 2,  "title": "Licensing of Drivers of Motor Vehicles",           "section_range": (3,  26)},
    {"number": 3,  "title": "Licensing of Conductors of Stage Carriages",       "section_range": (27, 38)},
    {"number": 4,  "title": "Registration of Motor Vehicles",                   "section_range": (39, 64)},
    {"number": 5,  "title": "Control of Transport Vehicles",                    "section_range": (65, 96)},
    {"number": 6,  "title": "Special Provisions: State Transport Undertakings", "section_range": (97,103)},
    {"number": 7,  "title": "Construction, Equipment and Maintenance",          "section_range":(104,116)},
    {"number": 8,  "title": "Control of Traffic",                               "section_range":(117,141)},
    {"number": 9,  "title": "Motor Vehicles Temporarily Leaving or Visiting India","section_range":(142,147)},
    {"number": 10, "title": "Liability Without Fault in Certain Cases",         "section_range":(148,150)},
    {"number": 11, "title": "Insurance Against Third Party Risks",              "section_range":(145,164)},
    {"number": 12, "title": "Claims Tribunals",                                 "section_range":(165,176)},
    {"number": 13, "title": "Offences, Penalties and Procedure",               "section_range":(177,210)},
    {"number": 14, "title": "Miscellaneous",                                    "section_range":(211,217)},
]

def scrape_mva_sections():
    """Scrape MVA sections from IndiaKanoon."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    print("\nScraping Motor Vehicles Act 1988 from IndiaKanoon...")

    # Step 1: Find the act document URL via search
    try:
        search_url = MVA_BASE + MVA_SEARCH
        r = requests.get(search_url, headers=headers, timeout=20)
        # Find act document links
        act_links = re.findall(r'href="(/doc/\d+/)"[^>]*>[^<]*Motor Vehicles Act', r.text, re.IGNORECASE)
        if not act_links:
            # Try broader: any doc link
            all_links = re.findall(r'href="(/doc/(\d+)/)"', r.text)
            print(f"  Search returned {len(all_links)} links. Trying direct known doc ID...")
            # Known IndiaKanoon doc ID for MV Act 1988
            act_path = "/doc/1362234/"
        else:
            act_path = act_links[0]
            print(f"  Found act at: {act_path}")
    except Exception as e:
        print(f"  Search failed: {e}")
        act_path = "/doc/1362234/"

    # Step 2: Get the act page and find all section links
    try:
        act_url = MVA_BASE + act_path
        print(f"  Fetching act page: {act_url}")
        r = requests.get(act_url, headers=headers, timeout=30)
        page_html = r.text
    except Exception as e:
        print(f"  Could not reach IndiaKanoon: {e}")
        return []

    # Find section anchors - IndiaKanoon uses <a href="/doc/DOCID/"> for sections
    # Pattern: Section N. Title  or  N. Title
    sec_pattern = re.compile(
        r'href="(/doc/(\d+)/?)"[^>]*>\s*(?:Section\s+)?(\d+)[.\s]',
        re.IGNORECASE
    )
    section_links = [(m.group(1), m.group(3)) for m in sec_pattern.finditer(page_html)]

    # Also try to find sections directly in the page text
    if not section_links:
        # Try extracting inline text from the page for any embedded section content
        inline_sections = re.findall(
            r'(\.\s*)?(?:Section\s+)?(\d+)\.\s+([A-Z][^.]{3,80})\.',
            page_html
        )
        if inline_sections:
            print(f"  Found {len(inline_sections)} inline section references")
        print(f"  No section links found in act page. IndiaKanoon structure may have changed.")
        return []

    # Deduplicate
    seen = set()
    unique_links = []
    for path, num in section_links:
        if num not in seen:
            seen.add(num)
            unique_links.append((path, int(num)))
    unique_links.sort(key=lambda x: x[1])
    print(f"  Found {len(unique_links)} unique section links")

    # Step 3: Scrape each section
    sections = []
    for doc_path, sec_num in unique_links:
        url = MVA_BASE + doc_path
        try:
            sr = requests.get(url, headers=headers, timeout=15)
            # Extract content from pre or div.judgments
            text_match = re.search(r'<pre[^>]*>(.*?)</pre>', sr.text, re.DOTALL)
            if not text_match:
                text_match = re.search(r'class="judgments"[^>]*>(.*?)</div>', sr.text, re.DOTALL)
            if text_match:
                raw = re.sub(r'<[^>]+>', ' ', text_match.group(1))
                raw = re.sub(r'\s{2,}', ' ', raw).strip()
            else:
                raw = ""

            # Extract title from content
            title_m = re.match(r'(?:Section\s+)?\d+\.?\s+([^.\n]{3,80})', raw)
            title = title_m.group(1).strip() if title_m else f"Section {sec_num}"

            sections.append({
                "section_number": sec_num,
                "section_title":  title,
                "content":        raw,
                "source_url":     url,
                "keywords":       get_keywords(raw),
            })
            print(f"  Scraped Section {sec_num}: {title[:40]} ({len(raw)} chars)")
            time.sleep(0.8)
        except Exception as e:
            print(f"  Error scraping section {sec_num}: {e}")

    return sections

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("MOTOR VEHICLES DB — FINAL EXTRACTOR")
    print("=" * 60)

    # ── 1. CMVR Rules ─────────────────────────────────────────────────────
    print("\n[1/2] Extracting CMVR 1989 Rules from PDFs...")
    all_cmvr_rules = []
    chapter_summary = {}

    files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".pdf"))
    for fname in files:
        meta = CHAPTER_META.get(fname, {"number": -1, "name": "Unknown", "rule_range": (0, 0)})
        print(f"\n  {fname} → Ch.{meta['number']}: {meta['name']}")

        if fname == "Appendices__1.pdf":
            rules = extract_appendix(fname, meta)
        else:
            rules = extract_chapter_rules(fname, meta)

        print(f"  → {len(rules)} rules extracted")
        if rules:
            nums = [r["rule_number"] for r in rules if isinstance(r["rule_number"], int)]
            if nums:
                print(f"  → Rule numbers: {min(nums)} – {max(nums)}")

        all_cmvr_rules.extend(rules)

        # Chapter summary
        ch = meta["number"]
        if ch not in chapter_summary:
            chapter_summary[ch] = {"chapter_number": ch, "chapter_name": meta["name"], "rule_count": 0}
        chapter_summary[ch]["rule_count"] += len(rules)

    # Sort CMVR rules
    def sort_key(r):
        ch = r.get("chapter_number", 99)
        rn = r.get("rule_number", 0)
        return (ch, rn if isinstance(rn, int) else 9999, str(rn))

    all_cmvr_rules.sort(key=sort_key)

    print(f"\n  CMVR TOTAL: {len(all_cmvr_rules)} rules")

    # ── 2. MVA Sections ───────────────────────────────────────────────────
    print("\n[2/2] Extracting Motor Vehicles Act 1988 sections...")
    mva_sections = scrape_mva_sections()
    print(f"  MVA TOTAL: {len(mva_sections)} sections scraped")

    # ── 3. Compile final DB ───────────────────────────────────────────────
    db = {
        "metadata": {
            "title":         "Motor Vehicles Act & Rules Database",
            "description":   "Structured dataset: Motor Vehicles Act 1988 + Central Motor Vehicles Rules 1989",
            "version":       "3.0",
            "last_updated":  "2026-02-19",
            "generated_by":  "Motor Vehicles DB Builder (Python)",
            "sources": [
                {"name": "MORTH", "url": "https://morth.gov.in",         "content": "CMVR 1989 PDFs"},
                {"name": "IndiaKanoon", "url": "https://indiankanoon.org","content": "MV Act 1988"},
            ],
            "statistics": {
                "total_cmvr_rules":    len(all_cmvr_rules),
                "total_mva_sections":  len(mva_sections),
                "cmvr_chapters":       7,
                "mva_chapters":        14,
            }
        },
        "acts": [
            {
                "title":        "Motor Vehicles Act, 1988",
                "short_title":  "MV Act 1988",
                "act_number":   "59 of 1988",
                "year":         1988,
                "ministry":     "Ministry of Road Transport and Highways",
                "chapters":     MVA_CHAPTERS,
                "total_sections": 217,
                "sections":     mva_sections,
                "note":         "" if mva_sections else "Sections could not be scraped. Provide data/mva_1988.pdf to populate.",
            }
        ],
        "rules": [
            {
                "title":           "Central Motor Vehicles Rules, 1989",
                "short_title":     "CMVR 1989",
                "year":            1989,
                "notification":    "G.S.R. 590(E), dated 2nd July, 1989",
                "ministry":        "Ministry of Road Transport and Highways",
                "chapter_summary": sorted(chapter_summary.values(), key=lambda x: x["chapter_number"]),
                "total_rules":     len(all_cmvr_rules),
                "rules":           all_cmvr_rules,
            }
        ],
    }

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print("\n" + "=" * 60)
    print("DONE!")
    print(f"  Output:       {OUTPUT_FILE}  ({size_kb:.1f} KB)")
    print(f"  CMVR rules:   {len(all_cmvr_rules)}")
    print(f"  MVA sections: {len(mva_sections)}")
    print("\nChapter breakdown (CMVR):")
    for ch in sorted(chapter_summary.values(), key=lambda x: x["chapter_number"]):
        print(f"  Ch {ch['chapter_number']:2d} | {ch['chapter_name'][:50]:50s} | {ch['rule_count']} rules")

if __name__ == "__main__":
    main()
