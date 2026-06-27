"""
Retriever Layer

Pipeline:

User Query
    ↓
Embed Query
    ↓
ChromaDB (HNSW)
    ↓
Top K Results
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

import chromadb
from src.embeddings.embedder import Embedder


class Retriever:
    def __init__(
        self,
        repository_name: str = None,
        persist_directory: str = None,
        collection_name: str = None,
    ):
        self.embedder = Embedder()

        if repository_name:
            from src.repository.repository_manager import validate_repository
            validate_repository(repository_name)
            self.persist_directory = f"data/chroma_db/{repository_name}"
            self.collection_name = f"repo_{repository_name}"
        else:
            self.persist_directory = persist_directory or "data/chroma_db"
            self.collection_name = collection_name or "archon_codebase"

        self.client = chromadb.PersistentClient(
            path=self.persist_directory
        )

        self.collection = self.client.get_collection(
            name=self.collection_name
        )

    def search(
        self,
        query: str,
        top_k: int = 20,
    ) -> list[dict]:
        """
        Search ChromaDB using semantic similarity.
        """

        query_embedding = self.embedder.embed_text(query)

        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
        )

        formatted_results = []

        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for symbol_id, metadata, distance in zip(ids, metadatas, distances):
            formatted_results.append(
                {
                    "symbol_id": symbol_id,
                    "repo": metadata.get("repo", "Unknown"),
                    "symbol_name": metadata.get(
                        "symbol_name",
                        "Unknown",
                    ),
                    "symbol_type": metadata.get(
                        "symbol_type",
                        "Unknown",
                    ),
                    "file": metadata.get(
                        "file",
                        "Unknown",
                    ),
                    "language": metadata.get(
                        "language",
                        "Unknown",
                    ),
                    "retrieval_text": metadata.get(
                        "retrieval_text",
                        "",
                    ),
                    "distance": float(distance),

                    "related_symbols": metadata.get(
                        "related_symbols",
                        [],
                    ),

                    "keywords": metadata.get(
                        "keywords",
                        [],
                    ), 

                    "signature": metadata.get(
                        "signature",
                        "",
                    ),  
                }
            )

        return formatted_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Retriever Layer.")
    parser.add_argument("repo_name", nargs="?", default=None, help="Name of the repository to query.")
    args = parser.parse_args()

    retriever = Retriever(repository_name=args.repo_name)

    query = input("\nAsk a question:\n> ")

    results = retriever.search(query=query, top_k=5)   

    print("\nTop Results\n")

    for rank, result in enumerate(results, start=1):
        print(f"{rank}. {result['symbol_name']} ({result['symbol_type']}) | Distance: {result['distance']:.4f}")
        print(f"Repository: {result['repo']}")
        print(f"File: {result['file']}")        
        print(f"Language: {result['language']}")        
        print(f"Context:")
        print(result["retrieval_text"])
        print()