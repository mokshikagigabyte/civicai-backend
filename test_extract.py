from pypdf import PdfReader

def extract_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    path = "data/cmvr_pdfs/CMVR-chapter1_1.pdf"
    print(extract_text(path)[:2000])
