"""
apply_embeddings.py
===================
Model selected: BAAI/bge-small-en-v1.5
  - Specifically trained for retrieval / RAG tasks (BGE = BAAI General Embedding)
  - 384-dimensional vectors (compact, fast)
  - 33M parameters — runs well on CPU
  - State-of-art on BEIR legal retrieval benchmarks
  - Beats all-MiniLM-L6-v2 by ~5% on retrieval tasks
  - Free, open-source on HuggingFace

Input : D:\moptor_vehical_dataset\motor_vehicles_rag_recursive.json
Output: D:\moptor_vehical_dataset\motor_vehicles_embedded.json
        D:\moptor_vehical_dataset\motor_vehicles_vectors.npz  (fast vector search)
"""

import json, os, time
import numpy as np
from sentence_transformers import SentenceTransformer

# ── Config ───────────────────────────────────────────────────────────────────
INPUT_JSON  = r"d:\MV_db\motor_vehicles_chunked.json"
OUTPUT_JSON = r"d:\MV_db\motor_vehicles_embedded.json"
VECTOR_NPZ  = r"d:\MV_db\motor_vehicles_embeddings.npy"
MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"  # Match main_app.py
BATCH_SIZE  = 32   # increase to 64 if you have >=8GB RAM

# BGE models require this prefix for retrieval passage encoding
BGE_PASSAGE_PREFIX = "Represent this sentence for searching relevant passages: "

def main():
    print("=" * 60)
    print("MOTOR VEHICLES RAG — EMBEDDING PIPELINE")
    print("=" * 60)
    print(f"Model  : {MODEL_NAME}")
    print(f"Input  : {INPUT_JSON}")
    print(f"Output : {OUTPUT_JSON}")
    print()

    # 1. Load chunks
    print("[1/4] Loading RAG chunks...")
    with open(INPUT_JSON, encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"  Loaded {len(chunks)} chunks")

    # 2. Load model
    print(f"\n[2/4] Loading model '{MODEL_NAME}'...")
    print("  (First run will download ~120 MB from HuggingFace)")
    t0 = time.time()
    model = SentenceTransformer(MODEL_NAME)
    print(f"  Model loaded in {time.time()-t0:.1f}s")
    print(f"  Embedding dimension: {model.get_sentence_embedding_dimension()}")

    # 3. Encode all chunk_texts
    print(f"\n[3/4] Encoding {len(chunks)} chunks (batch_size={BATCH_SIZE})...")
    print("  Adding BGE passage prefix for optimal retrieval quality...")

    texts = [BGE_PASSAGE_PREFIX + c["chunk_text"] for c in chunks]

    t1 = time.time()
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,   # L2-normalize → cosine similarity = dot product
        convert_to_numpy=True,
    )
    elapsed = time.time() - t1
    print(f"  Encoded in {elapsed:.1f}s  ({len(chunks)/elapsed:.1f} chunks/sec)")
    print(f"  Embedding shape: {embeddings.shape}")

    # 4. Attach embeddings to chunks
    print("\n[4/4] Attaching embeddings and saving...")
    for i, chunk in enumerate(chunks):
        chunk["embedding"] = embeddings[i].tolist()
        chunk["embedding_model"]  = MODEL_NAME
        chunk["embedding_dim"]    = int(embeddings.shape[1])
        chunk["embedding_normalized"] = True

    # Save full JSON (with embeddings in each chunk)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    # Save compact NPY for fast vector search
    np.save(VECTOR_NPZ, embeddings)

    json_kb = os.path.getsize(OUTPUT_JSON) / 1024
    npz_kb  = os.path.getsize(VECTOR_NPZ + ".npz" if not VECTOR_NPZ.endswith(".npz") else VECTOR_NPZ) / 1024

    print("\n" + "=" * 60)
    print("EMBEDDING COMPLETE")
    print("=" * 60)
    print(f"  Chunks embedded     : {len(chunks)}")
    print(f"  Embedding model     : {MODEL_NAME}")
    print(f"  Embedding dimension : {embeddings.shape[1]}")
    print(f"  Normalization       : L2 (cosine-ready)")
    print()
    print(f"  Output JSON  : {OUTPUT_JSON}  ({json_kb:.0f} KB)")
    print(f"  Vector store : {VECTOR_NPZ}  ({npz_kb:.0f} KB)")
    print()
    print("HOW TO USE:")
    print("-" * 40)
    print("  # Encode a query:")
    print("  from sentence_transformers import SentenceTransformer")
    print(f"  model = SentenceTransformer('{MODEL_NAME}')")
    print("  query_vec = model.encode('penalty for drunk driving',")
    print("                           normalize_embeddings=True)")
    print()
    print("  # Load vectors and search:")
    print("  import numpy as np")
    print(f"  data = np.load(r'{VECTOR_NPZ}')")
    print("  scores = data['embeddings'] @ query_vec   # dot product = cosine")
    print("  top_k  = scores.argsort()[-5:][::-1]")
    print("  for i in top_k:")
    print("      print(data['chunk_ids'][i], scores[i])")

    # Quick self-test — top result for a test query
    print("\n" + "=" * 60)
    print("SELF-TEST: Top 5 chunks for 'penalty for drunk driving'")
    print("=" * 60)
    query = model.encode("penalty for drunk driving", normalize_embeddings=True)
    scores = embeddings @ query
    top5  = scores.argsort()[-5:][::-1]
    for rank, idx in enumerate(top5, 1):
        print(f"  #{rank}  score={scores[idx]:.4f}  [{chunks[idx]['chunk_id']}]")
        print(f"       {chunks[idx]['section_title']}")
        print(f"       {chunks[idx]['chunk_text'][:120].strip()}...")
        print()

if __name__ == "__main__":
    main()
