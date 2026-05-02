"""
extract_cmvr_v2.py  —  Robust CMVR 1989 extractor
Improvements over v1:
  - Chapter-aware: knows which rule numbers belong to which chapter
  - Uses em-dash (—) as the definitive rule-start marker (CMVR style)
  - Handles fragmented PDF lines by joining them before parsing
  - Skips form/appendix sub-items (numbered lists inside a rule)
  - Produces clean JSON with all fields
"""

import os, re, json
from pypdf import PdfReader

DATA_DIR  = "data/cmvr_pdfs"
OUTPUT    = "data/cmvr_rules_v2.json"

# ── Chapter metadata ────────────────────────────────────────────────────────
CHAPTER_MAP = {
    "CMVR-chapter1_1.pdf": {"number": 1, "name": "Preliminary",                                     "rule_range": (1,  2)},
    "CMVR-chapter2_1.pdf": {"number": 2, "name": "Licensing of Drivers of Motor Vehicles",           "rule_range": (3,  30)},
    "CMVR-chapter3_1.pdf": {"number": 3, "name": "Registration of Motor Vehicles",                   "rule_range": (31, 90)},
    "CMVR-chapter4_1.pdf": {"number": 4, "name": "Control of Transport Vehicles",                    "rule_range": (91, 100)},
    "CMVR-chapter5_1.pdf": {"number": 5, "name": "Construction, Equipment and Maintenance",          "rule_range": (101,130)},
    "CMVR-chapter6_1.pdf": {"number": 6, "name": "Special Provisions – State Transport Undertakings","rule_range": (131,140)},
    "CMVR-chapter7_1.pdf": {"number": 7, "name": "Insurance Against Third Party Risks",              "rule_range": (141,163)},
    "Appendices__1.pdf":   {"number": 0, "name": "Appendices, Orders and Regulations",               "rule_range": (0,  0)},
}

# ── PDF text extraction ──────────────────────────────────────────────────────
def extract_pdf_text(path):
    try:
        reader = PdfReader(path)
        pages = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
        return pages
    except Exception as e:
        print(f"  ERROR reading {path}: {e}")
        return []

def join_pages(pages):
    """Join pages, inserting a page-break marker so we can strip page headers."""
    return "\n<<<PAGE>>>\n".join(pages)

def clean_raw_text(text):
    """Remove running headers, page numbers, and normalize whitespace."""
    # Remove page-break markers and surrounding lines (headers/footers)
    lines = text.split("\n")
    cleaned = []
    skip_next = 0
    for line in lines:
        stripped = line.strip()
        # Skip page-break marker lines
        if stripped == "<<<PAGE>>>":
            skip_next = 2          # skip the header line after page break
            continue
        if skip_next > 0:
            skip_next -= 1
            # But keep if it looks like a rule start
            if re.match(r'^\d+\.\s+\S', stripped):
                skip_next = 0
                cleaned.append(stripped)
            continue
        # Skip pure page-number lines
        if re.match(r'^\d{1,3}$', stripped):
            continue
        # Skip known running headers
        if "Central Motor Vehicles Rules" in stripped and len(stripped) < 60:
            continue
        if "CHAPTER" in stripped and len(stripped) < 40:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)

# ── Rule parsing for numbered chapters (1-7) ────────────────────────────────
# CMVR rule format:  "3.  General.—(1) Every application..."
# The em-dash (—) after the title is the definitive marker.
RULE_START = re.compile(
    r'(?:^|\n)\s*'           # start of line
    r'(\d{1,3})\.'           # rule number (1-3 digits)
    r'\s+'                   # whitespace
    r'([^.\n]{3,80}?)'       # rule title (3-80 chars, no period)
    r'[.\u2014\u2013\u2012]' # period or em/en dash
    r'(?=\s*[\(\[]?\s*(?:\(1\)|\(a\)|Every|No |The |A |An |In |For |Where|Subject|Provided|Save|Nothing|Any|All|Each|Upon|When|If |Unless|Notwithstanding))',
    re.MULTILINE
)

# Simpler fallback: just "N. Title.—" anywhere
RULE_START_SIMPLE = re.compile(
    r'(?:^|\n)\s*(\d{1,3})\.\s+([A-Z][^\n]{3,80}?)\s*[\u2014\u2013]',
    re.MULTILINE
)

def parse_chapter_rules(text, chapter_info, filename):
    """Parse rules from a chapter PDF using em-dash boundary detection."""
    rules = []
    lo, hi = chapter_info["rule_range"]

    # Try strict pattern first, fall back to simpler one
    matches = list(RULE_START.finditer(text))
    if len(matches) < 3:
        matches = list(RULE_START_SIMPLE.finditer(text))

    for i, m in enumerate(matches):
        num_str = m.group(1)
        title   = m.group(2).strip().rstrip('.')
        num     = int(num_str)

        # For numbered chapters, only keep rules in the expected range
        if lo > 0 and not (lo <= num <= hi + 20):   # +20 for tolerance
            continue

        # Content: from this match to next match (or end)
        start = m.start()
        end   = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end].strip()

        # Clean content
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]{2,}', ' ', content)
        content = re.sub(r'(\w)-\n\s*(\w)', r'\1\2', content)  # fix hyphenation
        content = content.strip()

        rules.append({
            "rule_number":   num,
            "rule_title":    title,
            "chapter_number": chapter_info["number"],
            "chapter_name":  chapter_info["name"],
            "source_file":   filename,
            "content":       content,
        })

    return rules

# ── Appendix parsing ─────────────────────────────────────────────────────────
# Appendices contain named sections like:
#   "APPENDIX I\nHIGH SECURITY REGISTRATION PLATES\n..."
#   "RULES OF THE ROAD REGULATIONS, 1989\n..."
#   "THE MOTOR VEHICLES (ALL INDIA PERMIT...) RULES, 1993\n..."

APPENDIX_SECTION = re.compile(
    r'(?:^|\n)((?:APPENDIX\s+[IVXLC]+|THE\s+[A-Z ]{10,}|RULES\s+OF\s+THE\s+ROAD|RENT\s+A\s+|SOLATIUM|LPG|NATIONAL\s+PERMIT)[^\n]{0,120})\n',
    re.MULTILINE
)

def parse_appendix(text, chapter_info, filename):
    """Parse appendix into named sections."""
    rules = []
    matches = list(APPENDIX_SECTION.finditer(text))

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.start()
        end   = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end].strip()
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]{2,}', ' ', content)
        content = re.sub(r'(\w)-\n\s*(\w)', r'\1\2', content)
        content = content.strip()

        # Also extract sub-rules within this appendix section
        sub_rules = list(RULE_START_SIMPLE.finditer(content))
        if sub_rules:
            # Parse each sub-rule
            for j, sr in enumerate(sub_rules):
                sr_num   = int(sr.group(1))
                sr_title = sr.group(2).strip().rstrip('.')
                sr_start = sr.start()
                sr_end   = sub_rules[j+1].start() if j+1 < len(sub_rules) else len(content)
                sr_content = content[sr_start:sr_end].strip()
                sr_content = re.sub(r'\n{3,}', '\n\n', sr_content)
                sr_content = re.sub(r'[ \t]{2,}', ' ', sr_content).strip()

                rules.append({
                    "rule_number":    f"App-{title[:30].replace(' ','_')}-{sr_num}",
                    "rule_title":     sr_title,
                    "chapter_number": 0,
                    "chapter_name":   chapter_info["name"],
                    "appendix_section": title,
                    "source_file":    filename,
                    "content":        sr_content,
                })
        else:
            # Whole section as one entry
            rules.append({
                "rule_number":    f"App-{i+1}",
                "rule_title":     title,
                "chapter_number": 0,
                "chapter_name":   chapter_info["name"],
                "appendix_section": title,
                "source_file":    filename,
                "content":        content,
            })

    return rules

# ── Keywords ─────────────────────────────────────────────────────────────────
KEYWORDS = [
    "driving licence","registration","permit","insurance","transport",
    "motor vehicle","highway","speed","accident","penalty","offence",
    "certificate","authority","licence","fitness","emission","fuel",
    "conductor","driver","owner","vehicle","road","traffic","tax",
    "weight","dimension","brake","horn","signal","overtaking","parking",
    "towing","goods","passenger","tourist","bus","truck","motorcycle",
    "ambulance","fire","police","court","fine","imprisonment",
]

def get_keywords(text):
    tl = text.lower()
    return sorted({kw for kw in KEYWORDS if kw in tl})

def count_sub_rules(text):
    return len(re.findall(r'\(\d+\)', text)) + len(re.findall(r'\([a-z]\)', text))

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    all_rules = []
    files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith('.pdf'))

    for filename in files:
        path = os.path.join(DATA_DIR, filename)
        ch   = CHAPTER_MAP.get(filename, {"number":-1,"name":"Unknown","rule_range":(0,0)})
        print(f"\nProcessing {filename} (Chapter {ch['number']}: {ch['name']})...")

        pages = extract_pdf_text(path)
        if not pages:
            print("  No text extracted!")
            continue
        print(f"  Pages: {len(pages)}")

        raw   = join_pages(pages)
        text  = clean_raw_text(raw)

        if filename == "Appendices__1.pdf":
            rules = parse_appendix(text, ch, filename)
        else:
            rules = parse_chapter_rules(text, ch, filename)

        print(f"  Rules found: {len(rules)}")
        if rules:
            nums = [r['rule_number'] for r in rules if isinstance(r['rule_number'], int)]
            if nums:
                print(f"  Rule numbers: {min(nums)} – {max(nums)}")

        # Enrich with keywords and sub_rules_count
        for r in rules:
            r["keywords"]        = get_keywords(r["content"])
            r["sub_rules_count"] = count_sub_rules(r["content"])

        all_rules.extend(rules)

    # Sort: chapter first, then rule number
    def sort_key(r):
        ch = r.get("chapter_number", 99)
        rn = r.get("rule_number", 0)
        if isinstance(rn, int):
            return (ch, rn, "")
        return (ch, 9999, str(rn))

    all_rules.sort(key=sort_key)

    # Build chapter summary
    ch_summary = {}
    for r in all_rules:
        ch = r.get("chapter_number", -1)
        if ch not in ch_summary:
            ch_summary[ch] = {"chapter_number": ch, "chapter_name": r.get("chapter_name",""), "rule_count": 0}
        ch_summary[ch]["rule_count"] += 1

    output = {
        "title":           "Central Motor Vehicles Rules, 1989",
        "short_title":     "CMVR 1989",
        "year":            1989,
        "notification":    "G.S.R. 590(E), dated 2nd July, 1989",
        "ministry":        "Ministry of Road Transport and Highways",
        "chapter_summary": sorted(ch_summary.values(), key=lambda x: x["chapter_number"]),
        "total_rules":     len(all_rules),
        "rules":           all_rules,
    }

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"TOTAL RULES EXTRACTED: {len(all_rules)}")
    print(f"Saved to: {OUTPUT}")
    print(f"\nChapter breakdown:")
    for ch in sorted(ch_summary.values(), key=lambda x: x["chapter_number"]):
        print(f"  Ch {ch['chapter_number']:2d} | {ch['chapter_name'][:50]:50s} | {ch['rule_count']} rules")

if __name__ == "__main__":
    main()
