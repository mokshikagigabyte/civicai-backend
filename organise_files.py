"""
organise_files.py
Creates D:/moptor_vehical_dataset/motor_vehicles_rag_dataset/ and copies all files.
"""
import os, shutil

BASE = "D:/moptor_vehical_dataset"
DEST = "D:/moptor_vehical_dataset/motor_vehicles_rag_dataset"

FILES = [
    "motor_vehicles_db.json",
    "motor_vehicles_rag_chunks.json",
    "motor_vehicles_rag_recursive.json",
    "motor_vehicles_embedded.json",
    "motor_vehicles_vectors.npz",
]

os.makedirs(DEST, exist_ok=True)
print(f"Created: {DEST}\n")

for fname in FILES:
    src = os.path.join(BASE, fname)
    dst = os.path.join(DEST, fname)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"  OK  {fname:45s}  {os.path.getsize(dst)/1024:>8.1f} KB")
    else:
        print(f"  MISS {fname}")

print("\nFolder contents:")
for f in sorted(os.listdir(DEST)):
    mb = os.path.getsize(os.path.join(DEST, f)) / (1024*1024)
    print(f"  {f:45s}  {mb:.2f} MB")

print(f"\nDone — {DEST}")
