import requests
import os

URLS = [
    "https://morth.nic.in/sites/default/files/Motor-Vehicles-Act-1988.pdf",
    "https://morth.gov.in/sites/default/files/Motor-Vehicles-Act-1988.pdf",
    "https://upload.indiacode.nic.in/showfile?actid=AC_CEN_5_23_00037_198859_1517807323906&type=rule&filename=The%20Motor%20Vehicles%20Act,%201988.pdf",
    "https://www.indiacode.nic.in/bitstream/123456789/1798/1/198859.pdf"
]

def download_mva():
    for i, url in enumerate(URLS):
        print(f"Trying {url}...")
        try:
            r = requests.get(url, stream=True, timeout=10, verify=False) # verify=False for gov sites sometimes
            if r.status_code == 200 and 'application/pdf' in r.headers.get('Content-Type', '').lower():
                print(f"Success! Downloading to data/mva_1988.pdf")
                with open("data/mva_1988.pdf", 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            else:
                print(f"Failed: {r.status_code} {r.headers.get('Content-Type')}")
        except Exception as e:
            print(f"Error: {e}")
    return False

if __name__ == "__main__":
    if download_mva():
        print("MVA 1988 PDF downloaded.")
    else:
        print("Could not download MVA 1988 PDF from known URLs.")
