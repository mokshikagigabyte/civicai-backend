"""
create_rag_chunks.py
====================
Creates semantic RAG chunks from motor_vehicles_db.json.

Rules:
- 600–900 tokens per chunk (approx 4 chars = 1 token)
- 10–20% overlap between chunks of the same rule
- Never mix two different rules/sections in one chunk
- Preserve subsection boundaries
- Keep original legal wording unchanged
- Output: motor_vehicles_rag_chunks.json

Run: python create_rag_chunks.py
"""

import json
import re
import os

INPUT_FILE  = r"D:\moptor_vehical_dataset\motor_vehicles_db.json"
OUTPUT_FILE = r"D:\moptor_vehical_dataset\motor_vehicles_rag_chunks.json"

# Token estimation: ~4 chars per token (legal text)
CHARS_PER_TOKEN = 4
TARGET_MIN = 600 * CHARS_PER_TOKEN   # 2400 chars
TARGET_MAX = 900 * CHARS_PER_TOKEN   # 3600 chars
OVERLAP_RATIO = 0.15                  # 15% overlap

# ── MVA Chapter lookup ────────────────────────────────────────────────────────
MVA_CHAPTER_MAP = {
    range(1,   3):  "Chapter I – Preliminary",
    range(3,  27):  "Chapter II – Licensing of Drivers of Motor Vehicles",
    range(27, 39):  "Chapter III – Licensing of Conductors of Stage Carriages",
    range(39, 65):  "Chapter IV – Registration of Motor Vehicles",
    range(65, 97):  "Chapter V – Control of Transport Vehicles",
    range(97, 104): "Chapter VI – Special Provisions: State Transport Undertakings",
    range(104,117): "Chapter VII – Construction, Equipment and Maintenance",
    range(117,142): "Chapter VIII – Control of Traffic",
    range(142,148): "Chapter IX – Motor Vehicles Temporarily Leaving India",
    range(148,151): "Chapter X – Liability Without Fault",
    range(151,165): "Chapter XI – Insurance Against Third Party Risks",
    range(165,177): "Chapter XII – Claims Tribunals",
    range(177,211): "Chapter XIII – Offences, Penalties and Procedure",
    range(211,218): "Chapter XIV – Miscellaneous",
}

CMVR_CHAPTER_NAMES = {
    0: "Appendices, Orders and Regulations",
    1: "Chapter I – Preliminary",
    2: "Chapter II – Licensing of Drivers of Motor Vehicles",
    3: "Chapter III – Registration of Motor Vehicles",
    4: "Chapter IV – Control of Transport Vehicles",
    5: "Chapter V – Construction, Equipment and Maintenance",
    6: "Chapter VI – Special Provisions: State Transport Undertakings",
    7: "Chapter VII – Insurance Against Third Party Risks",
}

def get_mva_chapter(section_number):
    for r, name in MVA_CHAPTER_MAP.items():
        if section_number in r:
            return name
    return "Unknown Chapter"

def estimate_tokens(text):
    return len(text) // CHARS_PER_TOKEN

def clean_chunk_text(text):
    """Remove excessive whitespace/symbols while keeping legal wording."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n +", "\n", text)
    # Remove stray PDF artifacts (page numbers between words)
    text = re.sub(r"(?<=\w)\s+\d{1,3}\s+(?=[A-Z])", " ", text)
    return text.strip()

def split_into_subsections(content):
    """
    Split a long rule/section into natural subsection boundaries.
    Looks for patterns: (1), (2), (a), (b), Provided that, Explanation, etc.
    Returns list of (prefix, text) tuples.
    """
    # Subsection boundary patterns
    SUBSEC = re.compile(
        r"(?:\n|^)(\s*(?:"
        r"\(\d+\)"          # (1), (2) ...
        r"|\([a-z]\)"       # (a), (b) ...
        r"|\([ivx]+\)"      # (i), (ii) ...
        r"|Provided that"
        r"|Explanation"
        r"|Exception"
        r"))",
        re.MULTILINE
    )
    splits = list(SUBSEC.finditer(content))
    if not splits:
        return [content]

    parts = []
    prev = 0
    for m in splits:
        chunk = content[prev:m.start()].strip()
        if chunk:
            parts.append(chunk)
        prev = m.start()
    parts.append(content[prev:].strip())
    return [p for p in parts if p]

def make_chunks_for_text(content, rule_num, rule_title, act_name, 
                          section_key, metadata_base):
    """
    Given a block of text for one rule/section, produce one or more chunks.
    - If content fits in 600-900 tokens: one chunk
    - If longer: split at subsection boundaries with 15% overlap
    """
    content = clean_chunk_text(content)
    chunks  = []

    token_count = estimate_tokens(content)

    if token_count <= 900:
        # Fits in one chunk — simple case
        chunks.append({
            "act_name":       act_name,
            "section_number": str(rule_num),
            "section_title":  rule_title,
            "chunk_id":       f"{section_key}_chunk_1",
            "chunk_text":     content,
            "metadata":       dict(metadata_base, chunk_index=1, total_chunks=1),
        })
        return chunks

    # Need to split — break at subsection boundaries
    parts = split_into_subsections(content)

    # Merge small parts into target-size windows
    windows = []
    current = []
    current_len = 0

    for part in parts:
        part_len = estimate_tokens(part)
        if current_len + part_len > 900 and current:
            windows.append("\n".join(current))
            # Overlap: carry last ~15% of current into next window
            overlap_chars = int(len("\n".join(current)) * OVERLAP_RATIO)
            overlap_text = "\n".join(current)[-overlap_chars:]
            current = [overlap_text, part]
            current_len = estimate_tokens(overlap_text) + part_len
        else:
            current.append(part)
            current_len += part_len

    if current:
        windows.append("\n".join(current))

    total = len(windows)
    for i, window in enumerate(windows, 1):
        window = clean_chunk_text(window)
        chunks.append({
            "act_name":       act_name,
            "section_number": str(rule_num),
            "section_title":  rule_title,
            "chunk_id":       f"{section_key}_chunk_{i}",
            "chunk_text":     window,
            "metadata":       dict(metadata_base, chunk_index=i, total_chunks=total),
        })

    return chunks

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"Loading {INPUT_FILE}...")
    with open(INPUT_FILE, encoding="utf-8") as f:
        db = json.load(f)

    all_chunks = []

    # ── 1. MVA 1988 sections ──────────────────────────────────────────────
    acts = db.get("acts", [])
    for act in acts:
        act_name = act.get("title", "Motor Vehicles Act, 1988")
        sections = act.get("sections", [])
        print(f"\nProcessing {act_name}: {len(sections)} sections")

        for sec in sections:
            sec_num   = sec.get("section_number", "?")
            sec_title = sec.get("section_title", f"Section {sec_num}")
            content   = sec.get("content", "").strip()

            if not content:
                continue

            chapter = get_mva_chapter(int(sec_num)) if str(sec_num).isdigit() else "Unknown"
            section_key = f"mva_s{sec_num}"

            meta = {
                "source":  "Motor Vehicles Act, 1988",
                "type":    "section",
                "chapter": chapter,
                "act":     "Motor Vehicles Act, 1988",
                "year":    1988,
            }

            chunks = make_chunks_for_text(
                content, sec_num, sec_title,
                act_name, section_key, meta
            )
            all_chunks.extend(chunks)

    print(f"  MVA chunks: {len(all_chunks)}")

    # ── 2. CMVR 1989 rules ───────────────────────────────────────────────
    rulesets = db.get("rules", [])
    cmvr_chunk_start = len(all_chunks)

    for ruleset in rulesets:
        ruleset_name = ruleset.get("title", "Central Motor Vehicles Rules, 1989")
        rules        = ruleset.get("rules", [])
        print(f"\nProcessing {ruleset_name}: {len(rules)} rules")

        for rule in rules:
            rule_num   = rule.get("rule_number", "?")
            rule_title = rule.get("rule_title", f"Rule {rule_num}")
            content    = rule.get("content",   "").strip()
            ch_num     = rule.get("chapter_number", -1)
            ch_name    = rule.get("chapter_name", "")
            app_sec    = rule.get("appendix_section", "")

            if not content:
                continue

            # Build chapter string
            if ch_num == 0:
                chapter_str = f"Appendices – {app_sec}" if app_sec else "Appendices, Orders and Regulations"
            else:
                chapter_str = CMVR_CHAPTER_NAMES.get(ch_num, ch_name)

            # Unique key
            safe_num = str(rule_num).replace("/", "_").replace(" ", "_")
            section_key = f"cmvr_r{safe_num}"

            meta = {
                "source":         "Central Motor Vehicles Rules, 1989",
                "type":           "rule",
                "chapter":        chapter_str,
                "chapter_number": ch_num,
                "act":            "Central Motor Vehicles Rules, 1989",
                "year":           1989,
                "source_pdf":     rule.get("source_file", ""),
                "keywords":       rule.get("keywords", []),
                "sub_rules_count": rule.get("sub_rules_count", 0),
            }

            if app_sec:
                meta["appendix_section"] = app_sec

            chunks = make_chunks_for_text(
                content, rule_num, rule_title,
                ruleset_name, section_key, meta
            )
            all_chunks.extend(chunks)

    cmvr_chunks = len(all_chunks) - cmvr_chunk_start
    print(f"  CMVR chunks: {cmvr_chunks}")

    # ── Save ───────────────────────────────────────────────────────────────
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    file_size = os.path.getsize(OUTPUT_FILE) / 1024

    print("\n" + "=" * 60)
    print("RAG CHUNKS COMPLETE")
    print("=" * 60)
    print(f"  Output file:   {OUTPUT_FILE}")
    print(f"  File size:     {file_size:.1f} KB")
    print(f"  Total chunks:  {len(all_chunks)}")
    print(f"  MVA chunks:    {len(all_chunks) - cmvr_chunks}")
    print(f"  CMVR chunks:   {cmvr_chunks}")

    # Token distribution
    token_counts = [estimate_tokens(c["chunk_text"]) for c in all_chunks]
    under = sum(1 for t in token_counts if t < 600)
    good  = sum(1 for t in token_counts if 600 <= t <= 900)
    over  = sum(1 for t in token_counts if t > 900)
    avg   = sum(token_counts) // len(token_counts)

    print(f"\n  Token distribution:")
    print(f"    < 600 tokens:      {under:4d} chunks  (short rules — normal)")
    print(f"    600–900 tokens:    {good:4d} chunks  (target range)")
    print(f"    > 900 tokens:      {over:4d} chunks  (extra-long rules)")
    print(f"    Average:           {avg:4d} tokens")
    print(f"\nSample chunk IDs:")
    for c in all_chunks[:3]:
        print(f"  {c['chunk_id']}: {c['section_title'][:50]} ({estimate_tokens(c['chunk_text'])} tokens)")

if __name__ == "__main__":
    main()
