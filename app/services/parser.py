import io
import re
from typing import List, Dict, Any
from pypdf import PdfReader
import tiktoken


class DocumentChunk:
    """Represents a chunk extracted from a document with layout metadata."""
    def __init__(
        self,
        content: str,
        page_number: int = 1,
        section_path: str = "General",
        chunk_index: int = 0
    ):
        self.content = content
        self.page_number = page_number
        self.section_path = section_path
        self.chunk_index = chunk_index


class DocumentParserService:
    """Extracts text from files and creates structure-aware chunks."""

    def __init__(self, target_chunk_tokens: int = 384, overlap_tokens: int = 50):
        self.target_chunk_tokens = target_chunk_tokens
        self.overlap_tokens = overlap_tokens
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    def _count_tokens(self, text: str) -> int:
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        # Fallback approximation: 1 token ≈ 4 characters
        return max(1, len(text) // 4)

    def extract_text_from_pdf(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """Extracts text per page from a PDF file."""
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_data = []

        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages_data.append({
                    "page_number": page_idx + 1,
                    "text": text
                })

        return pages_data

    def chunk_document(self, filename: str, file_bytes: bytes) -> List[DocumentChunk]:
        """
        Parses document by type and splits into structure-aware,
        page-tracked chunks of ~256-512 tokens.
        """
        chunks: List[DocumentChunk] = []
        chunk_counter = 0

        # Handle PDF
        if filename.lower().endswith(".pdf"):
            pages = self.extract_text_from_pdf(file_bytes)
        else:
            # Plain text / Markdown / Code
            text = file_bytes.decode("utf-8", errors="ignore")
            pages = [{"page_number": 1, "text": text}]

        for page in pages:
            page_num = page["page_number"]
            page_text = page["text"]

            # Split by paragraphs or double newlines first
            paragraphs = re.split(r"\n\s*\n", page_text)
            current_chunk_paras: List[str] = []
            current_tokens = 0
            current_heading = "General"

            for para in paragraphs:
                para_clean = para.strip()
                if not para_clean:
                    continue

                # Check if this paragraph looks like a heading
                # e.g., starts with # or is short and ends without a period
                if para_clean.startswith("#") or (len(para_clean) < 80 and not para_clean.endswith(".")):
                    current_heading = para_clean.lstrip("#").strip()

                para_tokens = self._count_tokens(para_clean)

                if current_tokens + para_tokens <= self.target_chunk_tokens:
                    current_chunk_paras.append(para_clean)
                    current_tokens += para_tokens
                else:
                    # Flush current chunk
                    if current_chunk_paras:
                        chunk_text = "\n\n".join(current_chunk_paras)
                        chunks.append(
                            DocumentChunk(
                                content=chunk_text,
                                page_number=page_num,
                                section_path=current_heading,
                                chunk_index=chunk_counter,
                            )
                        )
                        chunk_counter += 1

                    # Start next chunk (with a little overlap from previous paragraph if available)
                    if current_chunk_paras and self.overlap_tokens > 0:
                        overlap_para = current_chunk_paras[-1]
                        if self._count_tokens(overlap_para) <= self.overlap_tokens:
                            current_chunk_paras = [overlap_para, para_clean]
                            current_tokens = self._count_tokens(overlap_para) + para_tokens
                        else:
                            current_chunk_paras = [para_clean]
                            current_tokens = para_tokens
                    else:
                        current_chunk_paras = [para_clean]
                        current_tokens = para_tokens

            # Flush any remaining text on the page
            if current_chunk_paras:
                chunk_text = "\n\n".join(current_chunk_paras)
                chunks.append(
                    DocumentChunk(
                        content=chunk_text,
                        page_number=page_num,
                        section_path=current_heading,
                        chunk_index=chunk_counter,
                    )
                )
                chunk_counter += 1

        return chunks


parser_service = DocumentParserService()

