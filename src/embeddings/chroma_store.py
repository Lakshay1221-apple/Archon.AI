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
    def __init__(self, repo_name: str = None, persist_directory: str = None, collection_name: str = None):
        if repo_name:
            from src.repository.repository_manager import validate_repository
            validate_repository(repo_name)
            self.persist_directory = f"data/chroma_db/{repo_name}"
            self.collection_name = f"repo_{repo_name}"
        else:
            self.persist_directory = persist_directory or "data/chroma_db"
            self.collection_name = collection_name or "archon_codebase"

        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
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
                    "repo": record.get("repo", "Unknown"),
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
    import argparse

    parser = argparse.ArgumentParser(description="ChromaDB storage layer.")
    parser.add_argument("repo_name", nargs="?", default=None, help="Name of the repository to ingest.")
    args = parser.parse_args()

    if args.repo_name:
        store = ChromaStore(repo_name=args.repo_name)
        store.ingest(f"data/processed/{args.repo_name}/indexed_dataset.json")
    else:
        store = ChromaStore()
        store.ingest("data/processed/indexed_dataset.json")

