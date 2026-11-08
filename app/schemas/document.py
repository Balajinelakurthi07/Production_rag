import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department_id: uuid.UUID
    filename: str
    file_uri: str
    content_hash: str
    version: int
    mime_type: str
    created_at: datetime
    meta_info: Optional[Dict[str, Any]] = None


class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentResponse
    is_duplicate: bool
    total_chunks: int = 0

