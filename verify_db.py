import json

with open("data/motor_vehicles_db_final.json", encoding="utf-8") as f:
    db = json.load(f)

rules = db["rules"][0]
sections = db["acts"][0]["sections"]
ch_summary = rules["chapter_summary"]

print("=== FINAL DB VERIFICATION ===")
print(f"Version: {db['metadata']['version']}")
print(f"Total CMVR rules: {rules['total_rules']}")
print(f"Total MVA sections: {len(sections)}")
print()
print("Chapter breakdown:")
for ch in ch_summary:
    print(f"  Ch {ch['chapter_number']:2d} | {ch['chapter_name'][:52]:52s} | {ch['rule_count']:4d} rules")
print()
print("Sample rules (first 5):")
for r in rules["rules"][:5]:
    print(f"  [{r['chapter_number']}] Rule {r['rule_number']}: {r['rule_title'][:50]}")
    print(f"       keywords: {r['keywords'][:4]}")
    print(f"       sub_rules: {r['sub_rules_count']}")
    print()
