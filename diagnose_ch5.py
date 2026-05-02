"""
diagnose_ch5.py - Understand Chapter 5 PDF structure
Chapter 5 has 668 pages but only 22 rules extracted. Why?
"""
from pypdf import PdfReader
import re

EMDASH = "\u2014"
path = "data/cmvr_pdfs/CMVR-chapter5_1.pdf"

reader = PdfReader(path)
print(f"Total pages: {len(reader.pages)}")

# Sample pages at different points to understand structure
for page_idx in [0, 1, 2, 10, 50, 100, 200, 300, 400]:
    if page_idx >= len(reader.pages):
        continue
    t = reader.pages[page_idx].extract_text() or ""
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    print(f"\n--- Page {page_idx+1} (first 8 lines) ---")
    for line in lines[:8]:
        em = "EM" if EMDASH in line else "  "
        digit = "NUM" if re.match(r"^\d{1,3}\.", line) else "   "
        print(f"  {em} {digit}  {repr(line[:80])}")

# Count em-dash rule lines across first 50 pages
total_em = 0
rules_found = []
RULE_PAT = re.compile(r"^(\d{1,3})\.\s+(.{3,80}?)\u2014", re.MULTILINE)
for i, page in enumerate(reader.pages[:50]):
    t = page.extract_text() or ""
    matches = RULE_PAT.findall(t)
    for num, title in matches:
        rules_found.append((int(num), title[:50]))
        total_em += 1

print(f"\nEm-dash rules in first 50 pages: {total_em}")
print("Rules:", rules_found[:20])

# Check what format the forms/schedules use
print("\n\nSearching for FORM and SCHEDULE patterns in first 100 pages:")
form_count = 0
for i, page in enumerate(reader.pages[:100]):
    t = page.extract_text() or ""
    if "FORM" in t or "Schedule" in t.lower():
        form_lines = [l for l in t.split("\n") if "FORM" in l or "Schedule" in l.lower()]
        for fl in form_lines[:2]:
            print(f"  p{i+1}: {fl.strip()[:80]}")
        form_count += 1
print(f"Pages with FORM/Schedule: {form_count}")
