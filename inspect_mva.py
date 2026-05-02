import requests
from bs4 import BeautifulSoup

URL = "https://indiankanoon.org/doc/1715015/"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def inspect():
    r = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    links = soup.find_all('a', href=True)
    doc_links = [a for a in links if '/doc/' in a['href']]
    
    print(f"Total /doc/ links: {len(doc_links)}")
    for i, a in enumerate(doc_links[:20]):
        print(f"{i}: Text='{a.get_text().strip()}' Href='{a['href']}'")

if __name__ == "__main__":
    inspect()
