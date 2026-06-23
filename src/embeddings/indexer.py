"""
Indexer for generating embeddings from the embedding dataset.

Pipeline:

embedding_dataset.json
        ↓
Load Records
        ↓
Generate Embeddings
        ↓
Attach Metadata
        ↓
Return Indexed Records
"""

import sys
import json
from pathlib import Path

# Add project root directory to sys.path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

from src.embeddings.embedder import Embedder

class Indexer:
    def __init__(self):
        self.embedder = Embedder()

    def load_dataset(self, dataset_path: str) -> list[dict]:
        """
        Load embedding dataset JSON.

        Args:
            dataset_path: Path to embedding_dataset.json

        Returns:
            List of symbol records
        """
        path_obj = Path(dataset_path)

        with path_obj.open("r", encoding='utf-8') as f:
            return json.load(f)

    def build_index(self, dataset_path: str) -> list[dict]:
        """
        Generate embeddings for all retrieval candidates.

        Args:
            dataset_path: Path to embedding_dataset.json

        Returns:
            List of indexed records
        """

        records = self.load_dataset(dataset_path)

        texts = [
            record["retrieval_text"]
            for record in records 
        ]

        embeddings = self.embedder.embed_batch(texts)

        indexed_records = []

        for record, embedding in zip(records, embeddings):
            indexed_records.append(
                {
                    "symbol_id": record["symbol_id"],
                    "symbol_name": record["symbol_name"],
                    "symbol_type": record["symbol_type"],
                    "file": record["file"],
                    "language": record["language"],
                    "retrieval_text": record["retrieval_text"],

                    # vector
                    "embedding": embedding.tolist()
                }
            )
        return indexed_records

    def save_index(
        self,
        indexed_records: list[dict],
        output_path: str
    ):
        """
        Save the indexed records to a JSON file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(
                indexed_records,
                f,
                indent=2
            )


if __name__ == "__main__":

    indexer = Indexer()

    indexed_records = indexer.build_index(
        "data/processed/embedding_dataset.json"
    )

    indexer.save_index(
        indexed_records,
        "data/processed/indexed_dataset.json"
    )

    print(f"Indexed Records: {len(indexed_records)}")

    print("\nExample Record:\n")

    print(indexed_records[0])

