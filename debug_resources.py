import faiss
import pickle

try:
    index = faiss.read_index('motor_vehicles.faiss')
    print(f"FAISS Index Count: {index.ntotal}")
    
    with open('motor_vehicles_metadata.pkl', 'rb') as f:
        metadata = pickle.load(f)
    print(f"Metadata Count: {len(metadata)}")
    
    if index.ntotal != len(metadata):
        print("WARNING: FAISS index count and Metadata count mismatch!")
    else:
        print("SUCCESS: Index and Metadata counts match.")
        
    # Check for any None entries in metadata
    none_indices = [i for i, m in enumerate(metadata) if m is None]
    if none_indices:
        print(f"WARNING: Metadata contains None at indices: {none_indices[:10]}...")
    else:
        print("SUCCESS: No None entries in metadata.")

except Exception as e:
    print(f"Error checking resources: {e}")
