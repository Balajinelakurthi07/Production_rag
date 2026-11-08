import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.db import get_db
from app.core.security import get_current_user_context, AuthenticatedUserContext
from app.models.user import Department, Membership
from app.models.document import Document, Chunk
from app.services.ingestion import ingestion_service
from app.schemas.auth import DepartmentOut
from app.schemas.document import DepartmentCreate, DocumentResponse, DocumentUploadResponse

router = APIRouter(tags=["Documents & Departments"])


# ==========================================
# Department Management Endpoints
# ==========================================

@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    dept_in: DepartmentCreate,
    auth_ctx: AuthenticatedUserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db)
):
    """Creates a department and automatically assigns the creator as an admin member."""
    existing = await db.execute(select(Department).where(Department.name == dept_in.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department '{dept_in.name}' already exists."
        )

    dept = Department(name=dept_in.name, description=dept_in.description)
    db.add(dept)
    await db.flush()

    # Automatically add membership for the creator
    membership = Membership(
        user_id=auth_ctx.user.id,
        department_id=dept.id,
        role="admin"
    )
    db.add(membership)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.get("/departments", response_model=List[DepartmentOut])
async def list_user_departments(
    auth_ctx: AuthenticatedUserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db)
):
    """Lists only departments that the authenticated user belongs to."""
    if not auth_ctx.department_ids:
        return []

    result = await db.execute(
        select(Department).where(Department.id.in_(auth_ctx.department_ids))
    )
    return result.scalars().all()


# ==========================================
# Document Ingestion Endpoints
# ==========================================

@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    department_id: uuid.UUID = Form(..., description="Target department ID"),
    file: UploadFile = File(..., description="PDF or text document"),
    auth_ctx: AuthenticatedUserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads, parses, chunks, embeds, and indexes a document.
    Enforces strict Zero-Trust ACL: Rejects if user does not belong to the target department.
    """
    # 1. Zero-Trust ACL Check
    if department_id not in auth_ctx.department_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You are not an authorized member of this department."
        )

    # 2. Read file content
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    filename = file.filename or "untitled_doc"
    mime_type = file.content_type or "application/octet-stream"

    # 3. Trigger Ingestion Pipeline
    doc, is_duplicate = await ingestion_service.ingest_document(
        db=db,
        file_bytes=file_bytes,
        filename=filename,
        department_id=department_id,
        mime_type=mime_type,
    )

    # 4. Count total chunks created
    count_res = await db.execute(
        select(func.count(Chunk.id)).where(Chunk.doc_id == doc.id)
    )
    total_chunks = count_res.scalar_one()

    message = (
        "Document was previously indexed (idempotent skipped re-indexing)."
        if is_duplicate
        else f"Document successfully ingested into {total_chunks} chunks."
    )

    return DocumentUploadResponse(
        message=message,
        document=DocumentResponse.model_validate(doc),
        is_duplicate=is_duplicate,
        total_chunks=total_chunks,
    )


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    department_id: uuid.UUID,
    auth_ctx: AuthenticatedUserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Lists indexed documents within a department that the user has permission to access."""
    if department_id not in auth_ctx.department_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You are not authorized to view documents in this department."
        )

    result = await db.execute(
        select(Document).where(Document.department_id == department_id)
    )
    return result.scalars().all()

