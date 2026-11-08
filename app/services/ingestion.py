import hashlib
import io
import uuid
from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document, Chunk
from app.services.storage import storage_service
from app.services.parser import parser_service
from app.services.embedding import embedding_service


class IngestionService:
    """Orchestrates document hashing, storage, parsing, embedding, and indexing."""

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        """Computes the SHA-256 hexadecimal hash of raw file bytes."""
        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        return hasher.hexdigest()

    async def ingest_document(
        self,
        db: AsyncSession,
        file_bytes: bytes,
        filename: str,
        department_id: uuid.UUID,
        mime_type: str = "application/pdf",
    ) -> Tuple[Document, bool]:
        """
        Idempotently ingests a document.
        Returns: (Document, was_already_existing: bool)
        """
        content_hash = self.compute_sha256(file_bytes)

        # 1. Idempotency Check: check if already exists in this department
        query = select(Document).where(
            Document.department_id == department_id,
            Document.content_hash == content_hash,
        )
        result = await db.execute(query)
        existing_doc = result.scalar_one_or_none()

        if existing_doc:
            # Already ingested and unchanged! Return early.
            return existing_doc, True

        # 2. Upload raw file to S3
        file_obj = io.BytesIO(file_bytes)
        s3_key, s3_uri = storage_service.upload_file(
            file_obj=file_obj,
            filename=filename,
            department_id=department_id,
            content_type=mime_type,
        )

        # 3. Create Document DB entry
        new_doc = Document(
            department_id=department_id,
            filename=filename,
            file_uri=s3_uri,
            content_hash=content_hash,
            mime_type=mime_type,
            meta_info={"s3_key": s3_key, "file_size_bytes": len(file_bytes)},
        )
        db.add(new_doc)
        await db.flush()  # Flush to generate new_doc.id

        # 4. Parse & Chunk
        parsed_chunks = parser_service.chunk_document(filename, file_bytes)

        if parsed_chunks:
            # 5. Generate embeddings for all chunks in batch
            chunk_texts = [c.content for c in parsed_chunks]
            embeddings = embedding_service.embed_texts(chunk_texts)

            # 6. Bulk insert Chunks
            chunk_objects = []
            for idx, c in enumerate(parsed_chunks):
                chunk_obj = Chunk(
                    doc_id=new_doc.id,
                    department_id=department_id,
                    chunk_index=c.chunk_index,
                    page_number=c.page_number,
                    section_path=c.section_path,
                    content=c.content,
                    embedding=embeddings[idx] if idx < len(embeddings) else None,
                    enrichment={
                        "token_count": parser_service._count_tokens(c.content),
                    },
                )
                chunk_objects.append(chunk_obj)

            db.add_all(chunk_objects)

        await db.commit()
        await db.refresh(new_doc)
        return new_doc, False


ingestion_service = IngestionService()

