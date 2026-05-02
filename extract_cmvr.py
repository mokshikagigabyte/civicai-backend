import os
import re
import json
from pypdf import PdfReader

DATA_DIR = "data/cmvr_pdfs"
OUTPUT_FILE = "data/cmvr_rules.json"

def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

def clean_text(text):
    # Remove header/footer noise if possible (simple heuristic)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if "The Central Motor Vehicles Rules, 1989" in line:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def parse_rules(text):
    # Regex to match Rule start: "1. Short title..." or "2. Definitions..."
    # Looking for Number. Title
    # Note: PDF extraction often breaks lines, so we need to be careful.
    
    # Pattern: ^(\d+)\.\s+(.*?)[.—]
    # We will try to split by rule numbers.
    
    rules = []
    # Identify rule starts
    # This is a heuristic. It might miss some if formatting is bad.
    pattern = re.compile(r'\n(\d+)\.\s+([^\n]+?)[.—]')
    
    matches = list(pattern.finditer(text))
    
    for i in range(len(matches)):
        start_idx = matches[i].start()
        rule_num = matches[i].group(1)
        rule_title = matches[i].group(2).strip()
        
        # End index is start of next match or end of text
        if i + 1 < len(matches):
            end_idx = matches[i+1].start()
        else:
            end_idx = len(text)
            
        content = text[start_idx:end_idx].strip()
        # Remove the title line from content if desired, strictly it includes it matching the regex
        
        rules.append({
            "rule_number": rule_num,
            "rule_title": rule_title,
            "content": content
        })
        
    return rules

def main():
    all_rules = []
    
    # Process files in order
    files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')])
    
    for filename in files:
        path = os.path.join(DATA_DIR, filename)
        print(f"Processing {filename}...")
        raw_text = extract_text_from_pdf(path)
        cleaned_text = clean_text(raw_text)
        rules = parse_rules(cleaned_text)
        print(f"Found {len(rules)} rules in {filename}")
        
        # Add chapter info based on filename (rough)
        chapter_name = filename.replace(".pdf", "")
        for r in rules:
            r["source_file"] = filename
            
        all_rules.extend(rules)
        
    # Wrap in final structure
    final_data = {
        "title": "Central Motor Vehicles Rules, 1989",
        "rules": all_rules
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(all_rules)} rules to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
