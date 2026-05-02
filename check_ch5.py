"""check_ch5_count.py - How many em-dash rules actually exist in Ch5 PDF?"""
from pypdf import PdfReader
import re

EMDASH = "\u2014"
ENDASH = "\u2013"

path = "data/cmvr_pdfs/CMVR-chapter5_1.pdf"
reader = PdfReader(path)
text  = "\n".join(p.extract_text() or "" for p in reader.pages)

# Em-dash pattern
em_pat   = re.compile(r"(?:^|\n)\s*(\d{1,3})\.\s+([^\n]{3,100}?)\u2014", re.MULTILINE)
# Broader: any dash after title
broad_pat = re.compile(r"(?:^|\n)\s*(\d{1,3})\.\s+([A-Z][^\n]{3,100})[\u2014\u2013\-]", re.MULTILINE)

em_nums    = sorted(set(int(m.group(1)) for m in em_pat.finditer(text)))
broad_nums = sorted(set(int(m.group(1)) for m in broad_pat.finditer(text) if int(m.group(1)) >= 91))

print(f"Em-dash rules (>= 91): {[n for n in em_nums if n>=91]}")
print(f"Broad rules (>= 91):   {broad_nums[:30]}")
print(f"Em count (>=91): {len([n for n in em_nums if n>=91])}")
print(f"Broad count:     {len(broad_nums)}")
