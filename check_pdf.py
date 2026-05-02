import os
from pypdf import PdfReader

PDF_PATH = "data/mva_1988.pdf"

if os.path.exists(PDF_PATH):
    try:
        reader = PdfReader(PDF_PATH)
        print(f"PDF found. Pages: {len(reader.pages)}")
        print(reader.pages[0].extract_text()[:500])
    except Exception as e:
        print(f"PDF invalid: {e}")
else:
    print("PDF not found.")
