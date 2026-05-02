import json
import os

CMVR_FILE = "data/cmvr_rules.json"
MVA_FILE = "data/mva_1988_scraped.json" # Might have some stats or empty
OUTPUT_DB = "motor_vehicles_db.json"

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def main():
    db = {
        "metadata": {
            "title": "Motor Vehicles Act & Rules Database",
            "description": "Structured data for Motor Vehicles Act 1988 and Central Motor Vehicles Rules 1989.",
            "sources": [
                "MORTH (CMVR PDFs)",
                "Indian Kanoon (MVA Attempt)"
            ]
        },
        "acts": [],
        "rules": []
    }

    # Load CMVR
    cmvr_data = load_json(CMVR_FILE)
    if cmvr_data:
        db["rules"].append(cmvr_data)
        print(f"Loaded {len(cmvr_data.get('rules', []))} CMVR rules.")

    # Load MVA (if any)
    mva_data = load_json(MVA_FILE)
    if mva_data and len(mva_data) > 0:
         db["acts"].append({
            "title": "Motor Vehicles Act, 1988",
            "year": 1988,
            "sections": mva_data
        })
         print(f"Loaded {len(mva_data)} MVA sections (partial/scraped).")
    else:
        db["acts"].append({
            "title": "Motor Vehicles Act, 1988",
            "year": 1988,
            "note": "Full text could not be automatically extracted. Please provide 'data/mva_1988.pdf' or raw text to populate this section.",
            "sections": []
        })
        print("MVA data missing/empty.")

    with open(OUTPUT_DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    
    print(f"Database compiled to {OUTPUT_DB}")

if __name__ == "__main__":
    main()
