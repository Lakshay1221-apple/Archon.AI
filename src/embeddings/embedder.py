from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer(
            "BAAI/bge-small-en-v1.5"
        )

    def embed_text(self, text: str):
        return self.model.encode(
            text, 
            normalize_embeddings=True
        )

    def embed_batch(self, texts: list[str]):
        return self.model.encode(
            texts,
            normalize_embeddings=True
        )

if __name__ == "__main__":
    embedder = Embedder()
    
    texts = [
        "create payment",
        "initialize transaction",
        "weather in india"
    ]

    embeddings = embedder.embed_batch(texts)

    sim_1 = cosine_similarity(
        [embeddings[0]],
        [embeddings[1]]
    )

    sim_2 = cosine_similarity(
        [embeddings[0]],
        [embeddings[2]]
    )

    print(
        "payment vs transaction:",
        sim_1[0][0]
    )

    print(
        "payment vs weather:",
        sim_2[0][0]
    )