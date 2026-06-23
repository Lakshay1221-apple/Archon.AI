"""
ChromaDB Storage Layer

Responsibilities:

indexed_dataset.json
        ↓
Load Records
        ↓
Create Collection
        ↓
Store Embeddings
        ↓
Persist Database
"""

import sys
import json 
from pathlib import Path 

# Add project root directory to sys.path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

import chromadb

class ChromaStore:
    def __init__(self, persist_directory: str = "data/chroma_db", collection_name: str = "archon_codebase"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )

    def load_index(self, index_path: str) -> list[dict]:
        """
        Load indexed_dataset.json
        """
        path_obj = Path(index_path)
        with path_obj.open('r', encoding='utf-8') as f:
            return json.load(f)

    def ingest(self, index_path: str):
        records = self.load_index(index_path)

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for record in records:
            ids.append(record["symbol_id"])
            embeddings.append(record['embedding'])
            documents.append(record.get("retrieval_text", record["symbol_name"]))
            metadatas.append(
                {
                    "symbol_name": record["symbol_name"],
                    "symbol_type": record["symbol_type"],
                    "file": record["file"],
                    "language": record["language"],
                    "retrieval_text": record.get("retrieval_text", ""),
                }
            )
    
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )

        print(f"Stored {len(ids)} records in ChromaDB")
        
if __name__ == "__main__":
    store = ChromaStore()
    store.ingest(
        "data/processed/indexed_dataset.json"
    )
