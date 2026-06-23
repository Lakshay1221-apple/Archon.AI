"""
Manual Retriever

Pipeline:

User Query
    ↓
Embedding Model
    ↓
Query Vector
    ↓
Cosine Similarity
    ↓
Top K Results
"""

import sys
import json 
from pathlib import Path 

# Add project root directory to sys.path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

import numpy as np 
from sklearn.metrics.pairwise import cosine_similarity 
from src.embeddings.embedder import Embedder 

class ManualRetriever:
    def __init__(self, index_path: str):
        self.embedder = Embedder()
        self.index = self.load_index(index_path)
    
    def load_index(self, index_path: str) -> list[dict]:
        """
        Load indexed_dataset.json
        """
        path = Path(index_path)
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    
    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Search for the most relevant symbols for the given query.
        """
    
        query_embedder = self.embedder.embed_text(query)

        results = []

        for record in self.index:
            symbol_embedding = np.array(
                record["embedding"]
            )

            score = cosine_similarity(
                [query_embedder],
                [symbol_embedding]
            )[0][0]

            results.append(
                {
                    "score": float(score),
                    "symbol_id": record["symbol_id"],
                    "symbol_name": record["symbol_name"],
                    "symbol_type": record["symbol_type"],
                    "file": record["file"],
                    "language": record["language"],
                }
            )

        results.sort(
            key=lambda x: x['score'],
            reverse=True
        )

        return results[:top_k]

if __name__ == "__main__":

    retriever = ManualRetriever(
        "data/processed/indexed_dataset.json"
    )

    query = input(
        "\nAsk a question:\n> "
    )

    results = retriever.search(
        query=query,
        top_k=5
    )

    print("\nTop Results\n")

    for rank, result in enumerate(results, start=1):

        print(f"{rank}. {result['symbol_name']} ({result['symbol_type']}) | Score: {result['score']:.4f}")

        print(f"   File: {result['file']}")

        print()
