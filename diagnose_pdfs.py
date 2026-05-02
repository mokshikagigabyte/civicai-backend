"""
diagnose_pdfs.py - Understand actual PDF text format for all chapters
"""
from pypdf import PdfReader
import re
import os

DATA_DIR = "data/cmvr_pdfs"

CHAPTER_FILES = [
    "CMVR-chapter1_1.pdf",
    "CMVR-chapter2_1.pdf",
    "CMVR-chapter3_1.pdf",
    "CMVR-chapter4_1.pdf",
    "CMVR-chapter5_1.pdf",
    "CMVR-chapter6_1.pdf",
    "CMVR-chapter7_1.pdf",
]

# em-dash character
EMDASH = "\u2014"

# Simple pattern: lines that start with a number followed by period
RULE_PATTERN = re.compile(r"^(\d{1,3})\.\s+(.+)", re.MULTILINE)

for fname in CHAPTER_FILES:
    path = os.path.join(DATA_DIR, fname)
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"

    # Count matches with simple pattern
    all_matches = RULE_PATTERN.findall(text)
    # Only those with em-dash in title or content start
    em_matches = [(n, t) for n, t in all_matches if EMDASH in t]
    
    nums_all = sorted(set(int(m[0]) for m in all_matches))
    nums_em  = sorted(set(int(m[0]) for m in em_matches))
    
    print(f"\n{fname}:")
    print(f"  Total lines matching 'N. text': {len(all_matches)}")
    print(f"  Lines with em-dash:             {len(em_matches)}")
    print(f"  Rule numbers (all):  {nums_all[:10]} ... {nums_all[-5:] if len(nums_all) > 10 else ''}")
    print(f"  Rule numbers (em):   {nums_em[:10]} ... {nums_em[-5:] if len(nums_em) > 10 else ''}")
    print(f"  Sample lines:")
    for n, t in em_matches[:3]:
        print(f"    {n}. {t[:60]}")
