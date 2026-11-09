from typing import List
from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingService:
    """Free, local Hugging Face embedding generator using SentenceTransformers."""

    def __init__(self):
        self.dimension = settings.EMBEDDING_DIMENSION
        self.model_name = settings.EMBEDDING_MODEL_NAME
        print(f"Loading Hugging Face embedding model: {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        print("Hugging Face embedding model loaded successfully!")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates normalized vector embeddings for a batch of texts."""
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32
        )
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> List[float]:
        """Generates a normalized vector embedding for a single query."""
        results = self.embed_texts([query])
        return results[0] if results else [0.0] * self.dimension


embedding_service = EmbeddingService()
