import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import settings

CHROMA_PATH = Path(__file__).resolve().parent.parent / "mock_data" / "chroma"

# Safe imports for ChromaDB
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

class VectorStoreManager:
    """Manages the semantic search embeddings using ChromaDB or local fallback."""
    
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.fallback_db = [] # List of {"id": str, "text": str, "metadata": dict}
        
        if CHROMA_AVAILABLE:
            try:
                CHROMA_PATH.mkdir(parents=True, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
                self.collection = self.chroma_client.get_or_create_collection(name="nexusai_leads")
            except Exception as e:
                print(f"Error initializing ChromaDB: {e}. Falling back to in-memory store.")
                self.chroma_client = None
                self.collection = None
        else:
            print("ChromaDB package not available. Falling back to in-memory store.")

        # Load fallback DB if saved on disk
        self.fallback_file = CHROMA_PATH / "fallback_vectors.json"
        if not CHROMA_AVAILABLE or not self.collection:
            self._load_fallback_db()

    def _load_fallback_db(self):
        if self.fallback_file.exists():
            try:
                with open(self.fallback_file, "r", encoding="utf-8") as f:
                    self.fallback_db = json.load(f)
            except Exception as e:
                print(f"Error loading fallback database: {e}")
                self.fallback_db = []

    def _save_fallback_db(self):
        self.fallback_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.fallback_file, "w", encoding="utf-8") as f:
                json.dump(self.fallback_db, f, indent=2)
        except Exception as e:
            print(f"Error saving fallback database: {e}")

    def add_document(self, doc_id: str, text: str, metadata: Dict[str, Any]):
        if self.collection:
            try:
                # Add to chroma (it handles basic default embedding)
                self.collection.add(
                    documents=[text],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                return
            except Exception as e:
                print(f"ChromaDB write error: {e}. Writing to fallback.")
        
        # Fallback implementation
        # Remove old if exists
        self.fallback_db = [d for d in self.fallback_db if d["id"] != doc_id]
        self.fallback_db.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata
        })
        self._save_fallback_db()

    def similarity_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                formatted = []
                if results and "documents" in results and results["documents"]:
                    docs = results["documents"][0]
                    metas = results["metadatas"][0]
                    ids = results["ids"][0]
                    for d, m, i in zip(docs, metas, ids):
                        formatted.append({
                            "id": i,
                            "text": d,
                            "metadata": m
                        })
                return formatted
            except Exception as e:
                print(f"ChromaDB query error: {e}. Reading from fallback.")

        # Fallback implementation: simple Jaccard similarity or keyword matching
        query_words = set(query.lower().split())
        scored_docs = []
        for doc in self.fallback_db:
            doc_words = set(doc["text"].lower().split())
            intersection = query_words.intersection(doc_words)
            union = query_words.union(doc_words)
            score = len(intersection) / len(union) if union else 0.0
            scored_docs.append((score, doc))
            
        # Sort by score descending
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_docs[:limit]]

# Singleton Vector DB instance
vector_store = VectorStoreManager()
