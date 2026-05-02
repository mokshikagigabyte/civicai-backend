import requests
import sys

# Try to download from a likely stable URL or search result
# Since we can't browse easily, we will try to fetch from a known open repo or just search API
# Actually, let's try to just use requests to get the PDF if we can match the URL.
# The search result gave "indiacode.nic.in/...". 
# Let's try to search specifically for the PDF using a custom search-like approach or just fail over to IndianKanoon text.

# For this step, I will try to download from a known location if possible.
# If not, I will rely on the user to provide it or use text extraction from a different source.
# Let's try to fetch the India Code page for the Act and find the PDF link.

URL = "https://www.indiacode.nic.in/bitstream/123456789/1798/1/198859.pdf" 
# Note: This is a GUESS based on common handles. It might fail.
# A better approach is to try to find the handle.

def download_mva():
    try:
        print(f"Attempting to download {URL}...")
        r = requests.get(URL, stream=True, timeout=10)
        if r.status_code == 200 and 'application/pdf' in r.headers.get('Content-Type', ''):
            with open("data/mva_1988.pdf", 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Successfully downloaded MVA 1988 PDF.")
        else:
            print(f"Failed to download. Status: {r.status_code}, Type: {r.headers.get('Content-Type')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download_mva()
