"""
improve_db.py
Cleans and enriches motor_vehicles_db.json with the following improvements:
1. Removes footnote-only entries (rule_number is a footnote marker, not a real rule)
2. Cleans rule_title (removes partial footnote text like "Substituted by G", "Vide S")
3. Cleans content (removes page numbers, excessive whitespace, OCR artifacts)
4. Adds 'chapter' field to each rule based on source_file
5. Adds 'rule_type' field: 'rule', 'form', 'schedule', 'appendix', 'order'
6. Adds 'keywords' field: list of key terms extracted from content
7. Enriches metadata with version, last_updated, total_rules count
8. Fixes MVA acts section (removes wrong Limitation Act sections, adds proper placeholder)
9. Normalizes rule_number to integer where possible
10. Adds 'sub_rules' count per rule
"""

import json
import re
import os
from datetime import datetime

INPUT_FILE = "motor_vehicles_db.json"
OUTPUT_FILE = "motor_vehicles_db_improved.json"

# ─── Helpers ────────────────────────────────────────────────────────────────

FOOTNOTE_TITLE_PATTERNS = [
    r"^Substituted by [A-Z]",
    r"^Inserted by [A-Z]",
    r"^Inserted, ibid",
    r"^Vide [A-Z]",
    r"^Schedules? .* substituted",
    r"^See [A-Z]",
    r"^Added by [A-Z]",
    r"^Omitted by [A-Z]",
    r"^Renumbered",
    r"^Subs\.",
    r"^Ins\.",
]

FOOTNOTE_NUMBER_PATTERN = re.compile(r"^\d{4}$")  # e.g. "2001", "1993" — year-like footnote numbers

SOURCE_TO_CHAPTER = {
    "CMVR-chapter1_1.pdf": {"number": 1, "name": "Preliminary"},
    "CMVR-chapter2_1.pdf": {"number": 2, "name": "Licensing of Drivers of Motor Vehicles"},
    "CMVR-chapter3_1.pdf": {"number": 3, "name": "Registration of Motor Vehicles"},
    "CMVR-chapter4_1.pdf": {"number": 4, "name": "Control of Transport Vehicles"},
    "CMVR-chapter5_1.pdf": {"number": 5, "name": "Construction, Equipment and Maintenance of Motor Vehicles"},
    "CMVR-chapter6_1.pdf": {"number": 6, "name": "Special Provisions Relating to State Transport Undertakings"},
    "CMVR-chapter7_1.pdf": {"number": 7, "name": "Insurance of Motor Vehicles Against Third Party Risks"},
    "Appendices__1.pdf":   {"number": 0, "name": "Appendices, Orders and Regulations"},
}

RULE_TYPE_KEYWORDS = {
    "form":     ["Form No.", "FORM NO.", "APPLICATION FORM", "FORM OF APPLICATION", "SCHEDULE"],
    "order":    ["ORDER,", "ORDER 20", "ORDER 19"],
    "schedule": ["SCHEDULE", "THE FIRST SCHEDULE", "THE SECOND SCHEDULE", "THE THIRD SCHEDULE"],
    "appendix": ["APPENDIX", "APPENDIX I", "APPENDIX II", "APPENDIX III"],
}

LEGAL_KEYWORDS = [
    "driving licence", "registration", "permit", "insurance", "transport",
    "motor vehicle", "highway", "speed", "accident", "penalty", "offence",
    "certificate", "authority", "licence", "fitness", "emission", "fuel",
    "conductor", "driver", "owner", "vehicle", "road", "traffic", "tax",
    "weight", "dimension", "brake", "horn", "signal", "overtaking", "parking",
    "towing", "goods", "passenger", "tourist", "bus", "truck", "motorcycle",
    "ambulance", "fire", "police", "court", "fine", "imprisonment",
]

def is_footnote_entry(rule):
    """Returns True if this entry is a footnote/amendment note, not a real rule."""
    title = rule.get("rule_title", "")
    number = rule.get("rule_number", "")
    content = rule.get("content", "")

    # Year-like number (e.g. "2001") is a footnote
    if FOOTNOTE_NUMBER_PATTERN.match(str(number)):
        return True

    # Title matches footnote patterns
    for pat in FOOTNOTE_TITLE_PATTERNS:
        if re.match(pat, title, re.IGNORECASE):
            return True

    # Very short content that is just a footnote citation
    stripped = content.strip()
    if len(stripped) < 120 and re.match(r"^\d+\.\s+(Substituted|Inserted|Vide|Added|Omitted|See|Subs\.|Ins\.)", stripped):
        return True

    # Title is just a number (e.g. "2", "4") — likely a footnote marker
    if re.match(r"^\d+$", title.strip()):
        return True

    return False


def clean_content(text):
    """Clean raw PDF-extracted text."""
    if not text:
        return text

    # Remove page numbers like "\n5 \n", "\n 34 \n"
    text = re.sub(r'\n\s*\d{1,3}\s*\n', '\n', text)

    # Remove trailing page numbers at end of content
    text = re.sub(r'\n\s*\d{1,3}\s*$', '', text)

    # Normalize multiple blank lines to single
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove excessive spaces within lines
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # Fix hyphenated line breaks (common in PDFs): "motor ve-\nhicle" -> "motor vehicle"
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def clean_title(title):
    """Clean rule title."""
    if not title:
        return title
    # Remove trailing dots
    title = title.rstrip('.')
    # Normalize whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]
    return title


def normalize_rule_number(number):
    """Try to return an integer rule number, else keep as string."""
    try:
        n = int(str(number).strip())
        return n
    except (ValueError, TypeError):
        return str(number).strip()


def detect_rule_type(rule):
    """Detect the type of rule entry."""
    content = rule.get("content", "")
    title = rule.get("rule_title", "")
    combined = (content + " " + title).upper()

    for rtype, kws in RULE_TYPE_KEYWORDS.items():
        for kw in kws:
            if kw.upper() in combined:
                return rtype

    return "rule"


def extract_keywords(content):
    """Extract relevant legal keywords from content."""
    content_lower = content.lower()
    found = []
    for kw in LEGAL_KEYWORDS:
        if kw in content_lower:
            found.append(kw)
    return sorted(set(found))


def count_sub_rules(content):
    """Count sub-rule markers like (1), (2), (a), (b) etc."""
    numeric = len(re.findall(r'\(\d+\)', content))
    alpha = len(re.findall(r'\([a-z]\)', content))
    return numeric + alpha


def get_chapter_info(source_file):
    return SOURCE_TO_CHAPTER.get(source_file, {"number": -1, "name": "Unknown"})


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print(f"Loading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        db = json.load(f)

    # 1. Enrich metadata
    db["metadata"]["version"] = "2.0"
    db["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    db["metadata"]["generated_by"] = "Motor Vehicles DB Builder (Python)"
    db["metadata"]["sources"] = [
        {
            "name": "Ministry of Road Transport and Highways (MORTH)",
            "url": "https://morth.gov.in",
            "content": "Central Motor Vehicles Rules, 1989 (Chapters 1-7 + Appendices)",
            "format": "PDF"
        },
        {
            "name": "India Code",
            "url": "https://indiacode.nic.in",
            "content": "Motor Vehicles Act, 1988 (text pending)",
            "format": "Web/PDF"
        }
    ]

    # 2. Fix Acts section
    print("Fixing acts section...")
    db["acts"] = [
        {
            "title": "Motor Vehicles Act, 1988",
            "short_title": "MV Act 1988",
            "year": 1988,
            "act_number": "59 of 1988",
            "ministry": "Ministry of Road Transport and Highways",
            "description": (
                "An Act to consolidate and amend the law relating to motor vehicles. "
                "It covers licensing of drivers, registration of vehicles, control of transport vehicles, "
                "construction and maintenance standards, insurance, and penalties."
            ),
            "chapters": [
                {"number": 1, "title": "Preliminary"},
                {"number": 2, "title": "Licensing of Drivers of Motor Vehicles"},
                {"number": 3, "title": "Licensing of Conductors of Stage Carriages"},
                {"number": 4, "title": "Registration of Motor Vehicles"},
                {"number": 5, "title": "Control of Transport Vehicles"},
                {"number": 6, "title": "Special Provisions Relating to State Transport Undertakings"},
                {"number": 7, "title": "Construction, Equipment and Maintenance of Motor Vehicles"},
                {"number": 8, "title": "Control of Traffic"},
                {"number": 9, "title": "Motor Vehicles Temporarily Leaving or Visiting India"},
                {"number": 10, "title": "Liability Without Fault in Certain Cases"},
                {"number": 11, "title": "Insurance of Motor Vehicles Against Third Party Risks"},
                {"number": 12, "title": "Claims Tribunals"},
                {"number": 13, "title": "Offences, Penalties and Procedure"},
                {"number": 14, "title": "Miscellaneous"},
            ],
            "total_sections": 217,
            "note": (
                "Full section text is not yet available. "
                "To populate this section, provide the PDF from https://indiacode.nic.in/handle/123456789/1798 "
                "and run the extraction script."
            ),
            "sections": []
        }
    ]

    # 3. Process CMVR rules
    print("Processing CMVR rules...")
    original_rules = db["rules"][0]["rules"]
    print(f"  Original rule count: {len(original_rules)}")

    cleaned_rules = []
    footnote_count = 0

    for rule in original_rules:
        if is_footnote_entry(rule):
            footnote_count += 1
            continue

        chapter_info = get_chapter_info(rule.get("source_file", ""))
        content_cleaned = clean_content(rule.get("content", ""))
        title_cleaned = clean_title(rule.get("rule_title", ""))

        enriched = {
            "rule_number": normalize_rule_number(rule.get("rule_number", "")),
            "rule_title": title_cleaned,
            "chapter_number": chapter_info["number"],
            "chapter_name": chapter_info["name"],
            "source_file": rule.get("source_file", ""),
            "rule_type": detect_rule_type(rule),
            "content": content_cleaned,
            "keywords": extract_keywords(content_cleaned),
            "sub_rules_count": count_sub_rules(content_cleaned),
        }
        cleaned_rules.append(enriched)

    print(f"  Footnote entries removed: {footnote_count}")
    print(f"  Clean rules remaining: {len(cleaned_rules)}")

    # Sort rules: by chapter_number, then rule_number
    def sort_key(r):
        ch = r.get("chapter_number", 99)
        rn = r.get("rule_number", 0)
        if isinstance(rn, int):
            return (ch, rn, "")
        return (ch, 9999, str(rn))

    cleaned_rules.sort(key=sort_key)

    # Build chapter summary
    chapter_summary = {}
    for r in cleaned_rules:
        ch = r.get("chapter_number", -1)
        ch_name = r.get("chapter_name", "Unknown")
        if ch not in chapter_summary:
            chapter_summary[ch] = {"chapter_number": ch, "chapter_name": ch_name, "rule_count": 0}
        chapter_summary[ch]["rule_count"] += 1

    db["rules"] = [
        {
            "title": "Central Motor Vehicles Rules, 1989",
            "short_title": "CMVR 1989",
            "year": 1989,
            "notification": "G.S.R. 590(E), dated 2nd July, 1989",
            "ministry": "Ministry of Road Transport and Highways",
            "description": (
                "Rules made under the Motor Vehicles Act, 1988, covering detailed procedures for "
                "licensing, registration, permits, construction standards, insurance, and road regulations."
            ),
            "chapter_summary": sorted(chapter_summary.values(), key=lambda x: x["chapter_number"]),
            "total_rules": len(cleaned_rules),
            "rules": cleaned_rules
        }
    ]

    # 4. Final metadata stats
    db["metadata"]["statistics"] = {
        "total_acts": len(db["acts"]),
        "total_rulesets": len(db["rules"]),
        "total_cmvr_rules": len(cleaned_rules),
        "footnote_entries_removed": footnote_count,
        "cmvr_chapters_covered": 7,
        "cmvr_appendices_covered": 1,
    }

    # 5. Save
    print(f"Saving improved database to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\nDone!")
    print(f"   Output file: {OUTPUT_FILE}")
    print(f"   File size: {size_kb:.1f} KB")
    print(f"   Total CMVR rules (clean): {len(cleaned_rules)}")
    print(f"   Footnote entries removed: {footnote_count}")
    print(f"   Acts in database: {len(db['acts'])}")

if __name__ == "__main__":
    main()
