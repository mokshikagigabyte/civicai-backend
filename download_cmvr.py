import os
import requests

DATA_DIR = "data/cmvr_pdfs"
os.makedirs(DATA_DIR, exist_ok=True)

URLS = [
    "https://morth.gov.in/sites/default/files/CMVR-chapter1_1.pdf",
    "https://morth.gov.in/sites/default/files/CMVR-chapter2_1.pdf",
    "https://morth.gov.in/sites/default/files/CMVR-chapter3_1.pdf",
    "https://morth.gov.in/sites/default/files/CMVR-chapter4_1.pdf",
    "https://morth.gov.in/sites/default/files/CMVR-chapter5_1.pdf",
    "https://morth.gov.in/sites/default/files/CMVR-chapter6_1.pdf",
    "https://morth.gov.in/sites/default/files/CMVR-chapter7_1.pdf",
    "https://morth.gov.in/sites/default/files/Appendices%20_1.pdf"
]

def download_file(url):
    local_filename = url.split('/')[-1]
    # fix %20
    local_filename = local_filename.replace("%20", "_")
    path = os.path.join(DATA_DIR, local_filename)
    
    print(f"Downloading {url} to {path}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        print("Done.")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

if __name__ == "__main__":
    for url in URLS:
        download_file(url)
