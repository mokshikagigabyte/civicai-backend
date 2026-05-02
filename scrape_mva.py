import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re

BASE_URL = "https://indiankanoon.org"
# Main doc for Motor Vehicles Act 1988
START_URL = "https://indiankanoon.org/doc/1715015/"
OUTPUT_FILE = "data/mva_1988_scraped.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def scrape_mva():
    print(f"Fetching TOC from {START_URL}...")
    soup = get_soup(START_URL)
    if not soup:
        return

    # Find links to sections
    # Structure: Links are usually in the format /doc/ID/
    # We look for links that contain "Section" in their text or usage
    
    # Acts on Indian Kanoon often replace the main view with the full text or a list of sections.
    # For MVA 1988, doc 1715015 acts as the central node.
    
    sections = []
    
    # Try to find the list of sections. 
    # Sometimes it's a "Central Acts" listing.
    # Let's verify if 1715015 is the FULL ACT or just the COVER.
    # Usually it lists sections at the bottom or in a "judgments" or "expanded" view.
    # But often IndianKanoon docs have cross-links.
    
    # Heuristic: Find all links to indiankanoon.org/doc/
    # Filter those that look like sections.
    
    links = soup.find_all('a', href=True)
    section_links = []
    
    for a in links:
        href = a['href']
        text = a.get_text().strip()
        # Check if it references a doc and text starts with "Section"
        if "/doc/" in href and (text.startswith("Section") or re.match(r'^Section \d+', text)):
            full_url = BASE_URL + href if href.startswith('/') else href
            section_links.append((text, full_url))
            
    # Remove duplicates preserving order
    unique_links = []
    seen = set()
    for text, url in section_links:
        if url not in seen:
            unique_links.append((text, url))
            seen.add(url)
            
    print(f"Found {len(unique_links)} potential section links.")
    
    scraped_data = []
    
    for title, url in unique_links:
        print(f"Scraping {title}...")
        s_soup = get_soup(url)
        if s_soup:
            # Extract content. Usually in <div class="doc_content"> or similar
            # Indian Kanoon structure: 
            # <div class="judgments"> ... </div> or plain text
            
            # Try to simplify: get text
            content_div = s_soup.find('div', {'class': 'doc_content'}) # This class might vary, often it's 'main_text' or check specific site structure
             # Actually, often it is implicitly the body text minus header/footer.
             # Inspection of IndianKanoon structure: <div class="doc_content"> is common? Or <div id="p_1"> etc.
             
            # Fallback: get all text
            content = s_soup.get_text(separator='\n')
            
            # Simple cleanup
            # We want the text after the title
            
            scraped_data.append({
                "section_title": title,
                "url": url,
                "content": content[:2000] + "..." # Truncate for now to save space in preview, or save FULL.
                # Actually, we want full content.
            })
        
        time.sleep(1) # Be polite
        
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, indent=2)
        
    print(f"Saved {len(scraped_data)} sections to {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape_mva()
