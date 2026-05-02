import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import os

class LegalRAG:
    def __init__(self, index_path='motor_vehicles.faiss', metadata_path='motor_vehicles_metadata.pkl', skip_load=False):
        # Get the project root directory (parent of this submodule)
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.index_path = os.path.join(self.root_dir, index_path)
        self.metadata_path = os.path.join(self.root_dir, metadata_path)
        
        # skip_load=True when resources are injected externally (M4 fix)
        if skip_load:
            self.index = None
            self.metadata = None
            self.model = None
            print("LegalRAG: Using pre-loaded resources (skip_load=True).")
            return

        print(f"Loading FAISS index from {self.index_path}")
        self.index = faiss.read_index(self.index_path)
        
        print(f"Loading metadata from {self.metadata_path}")
        with open(self.metadata_path, 'rb') as f:
            self.metadata = pickle.load(f)
            
        print("Loading embedding model...")
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    def retrieve(self, query: str, top_k: int = 5):
        query_embedding = self.model.encode([query]).astype('float32')
        distances, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1: continue
            data = self.metadata[idx]
            results.append({
                "act_name": data['act_name'],
                "section_number": data['section_number'],
                "section_title": data['section_title'],
                "text": data['text'],
                "punishment": data.get('punishment', 'Not Specified'),
                "score": float(distances[0][i])
            })
        return results

    def format_context(self, results):
        context_parts = []
        for res in results:
            part = f"ACT: {res['act_name']}, SECTION: {res['section_number']} - {res['section_title']}\nTEXT: {res['text']}\nPUNISHMENT: {res['punishment']}"
            context_parts.append(part)
        return "\n\n---\n\n".join(context_parts)
