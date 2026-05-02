import requests
import os
import warnings
warnings.filterwarnings('ignore')

os.makedirs('data', exist_ok=True)

# Try IndiaCode PDF
url = 'https://www.indiacode.nic.in/bitstream/123456789/1798/1/198859.pdf'
print('Trying IndiaCode PDF...')
try:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    r = requests.get(url, timeout=30, verify=False, headers=headers)
    ct = r.headers.get('Content-Type', '')
    print(f'Status: {r.status_code}, Content-Type: {ct}')
    print(f'Content length: {len(r.content)} bytes')
    if r.status_code == 200 and len(r.content) > 10000:
        with open('data/mva_1988.pdf', 'wb') as f:
            f.write(r.content)
        print('Saved to data/mva_1988.pdf')
    else:
        print('Download failed or too small')
except Exception as e:
    print(f'Error: {e}')

# Check existing CMVR PDFs
print('\nChecking existing CMVR PDFs:')
cmvr_dir = 'data/cmvr_pdfs'
if os.path.exists(cmvr_dir):
    for f in sorted(os.listdir(cmvr_dir)):
        if f.endswith('.pdf'):
            size = os.path.getsize(os.path.join(cmvr_dir, f))
            print(f'  {f}: {size/1024:.1f} KB')
else:
    print('  No CMVR PDFs found')
