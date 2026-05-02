"""
diagnose_ch45.py - Check exact rule numbers in chapters 4 and 5
"""
from pypdf import PdfReader
import re, os

EMDASH = "\u2014"
RULE_BOUNDARY = re.compile(
    r"(?:^|\n)\s*(\d{1,3})\.\s+([^\n]{3,100}?)\u2014",
    re.MULTILINE
)

for fname in ["CMVR-chapter4_1.pdf", "CMVR-chapter5_1.pdf", "CMVR-chapter6_1.pdf"]:
    path = os.path.join("data/cmvr_pdfs", fname)
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"

    matches = list(RULE_BOUNDARY.finditer(text))
    nums = sorted(set(int(m.group(1)) for m in matches))
    print(f"\n{fname}:")
    print(f"  All rule numbers found: {nums}")
    print(f"  Total matches: {len(matches)}")
    for m in matches[:5]:
        print(f"  Sample: {m.group(1)}. {m.group(2)[:50]}...")
