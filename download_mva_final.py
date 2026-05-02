"""
download_mva_final.py
Tries multiple strategies to download the Motor Vehicles Act 1988 PDF.
"""
import requests
import os
import warnings
warnings.filterwarnings('ignore')

os.makedirs('data', exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
    'Accept': 'application/pdf,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.indiacode.nic.in/',
}

URLS = [
    # IndiaCode direct bitstream
    'https://www.indiacode.nic.in/bitstream/123456789/1798/1/198859.pdf',
    # IndiaCode alternate
    'https://www.indiacode.nic.in/bitstream/123456789/1798/3/A1988-59.pdf',
    # Legislative dept
    'https://lddashboard.legislative.gov.in/sites/default/files/A1988-59.pdf',
    # MORTH
    'https://morth.nic.in/sites/default/files/Motor-Vehicles-Act-1988.pdf',
    'https://morth.gov.in/sites/default/files/Motor-Vehicles-Act-1988.pdf',
    # egazette
    'https://egazette.nic.in/WriteReadData/1988/E-1988-11-0001-198859.pdf',
    # Another common mirror
    'https://upload.indiacode.nic.in/showfile?actid=AC_CEN_5_23_00037_198859_1517807323906&type=rule&filename=The%20Motor%20Vehicles%20Act,%201988.pdf',
]

def try_download(url):
    try:
        session = requests.Session()
        r = session.get(url, headers=HEADERS, timeout=30, verify=False, allow_redirects=True)
        ct = r.headers.get('Content-Type', '')
        size = len(r.content)
        print(f'  Status={r.status_code}, CT={ct[:40]}, Size={size} bytes, FinalURL={r.url[:80]}')
        
        # Check if it's actually a PDF (starts with %PDF)
        if size > 50000 and (r.content[:4] == b'%PDF' or 'pdf' in ct.lower()):
            return r.content
        return None
    except Exception as e:
        print(f'  Error: {e}')
        return None

print('Attempting to download Motor Vehicles Act 1988 PDF...\n')
for url in URLS:
    print(f'Trying: {url[:80]}...')
    data = try_download(url)
    if data:
        with open('data/mva_1988.pdf', 'wb') as f:
            f.write(data)
        print(f'\nSUCCESS! Saved {len(data)/1024:.1f} KB to data/mva_1988.pdf')
        break
    print()
else:
    print('\nAll URLs failed. MVA PDF could not be downloaded automatically.')
    print('Please manually download from:')
    print('  https://www.indiacode.nic.in/handle/123456789/1798')
    print('  and save as data/mva_1988.pdf')
