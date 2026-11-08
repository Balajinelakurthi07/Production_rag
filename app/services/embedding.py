from typing import List
import numpy as np

from app.config import settings


class EmbeddingService:
    """Provider-agnostic embedding generator (OpenAI or Local SentenceTransformers)."""

    def __init__(self):
        self.dimension = settings.EMBEDDING_DIMENSION
        self.openai_client = None
        self.local_model = None

        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                print(f"Using OpenAI Embedding Service: {settings.EMBEDDING_MODEL_NAME}")
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}, falling back to local model.")

        if self.openai_client is None:
            # Fallback to local SentenceTransformer
            try:
                from sentence_transformers import SentenceTransformer
                self.local_model = SentenceTransformer("all-MiniLM-L6-v2")
                print("Using local SentenceTransformer embedding model: all-MiniLM-L6-v2")
            except Exception as e:
                print(f"Warning: could not load sentence-transformers: {e}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of texts."""
        if not texts:
            return []

        # If OpenAI is active
        if self.openai_client:
            response = self.openai_client.embeddings.create(
                input=texts,
                model=settings.EMBEDDING_MODEL_NAME
            )
            return [data.embedding for data in response.data]

        # If local model is active
        if self.local_model:
            raw_embeddings = self.local_model.encode(texts, normalize_embeddings=True)
            results = []
            for emb in raw_embeddings:
                emb_list = emb.tolist()
                # If database expects 1536 dimensions and local model produces 384,
                # pad with zeros to match schema dimension
                if len(emb_list) < self.dimension:
                    emb_list = emb_list + [0.0] * (self.dimension - len(emb_list))
                elif len(emb_list) > self.dimension:
                    emb_list = emb_list[:self.dimension]
                results.append(emb_list)
            return results

        # Ultimate fallback dummy (for unit testing environments without model weights)
        return [[0.0] * self.dimension for _ in texts]

    def embed_query(self, query: str) -> List[float]:
        """Generates embedding for a single query."""
        results = self.embed_texts([query])
        return results[0] if results else [0.0] * self.dimension


embedding_service = EmbeddingService()

