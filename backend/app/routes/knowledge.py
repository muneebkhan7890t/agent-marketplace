"""
routes/knowledge.py
--------------------
Endpoints for managing a business's RAG knowledge base: upload docs (as raw
text or a .txt/.md file), list/delete them, and test what the retriever
would pull back for a given customer question.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business
from app.services.knowledge_base import KnowledgeBaseService

router = APIRouter()


class AddDocumentBody(BaseModel):
    business_id: int
    title: str
    content: str


def _get_owned_business(business_id: int, current_user: User, db: Session) -> Business:
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


# ------------------------------------------------------------------ #
# Add a document (raw text)
# ------------------------------------------------------------------ #

@router.post("/documents")
def add_document(
    body: AddDocumentBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add (or replace) a knowledge base document from pasted text."""
    _get_owned_business(body.business_id, current_user, db)

    result = KnowledgeBaseService().add_document(
        business_id=body.business_id,
        title=body.title,
        content=body.content,
    )
    return result


# ------------------------------------------------------------------ #
# Add a document (file upload: .txt / .md)
# ------------------------------------------------------------------ #

@router.post("/upload")
async def upload_document(
    business_id: int = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add (or replace) a knowledge base document from an uploaded .txt/.md file."""
    _get_owned_business(business_id, current_user, db)

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be plain text (.txt or .md)")

    result = KnowledgeBaseService().add_document(
        business_id=business_id,
        title=title,
        content=text,
    )
    return result


# ------------------------------------------------------------------ #
# List documents
# ------------------------------------------------------------------ #

@router.get("/documents")
def list_documents(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_business(business_id, current_user, db)
    return KnowledgeBaseService().list_documents(business_id)


# ------------------------------------------------------------------ #
# Delete a document
# ------------------------------------------------------------------ #

@router.delete("/documents")
def delete_document(
    business_id: int = Query(...),
    title: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_business(business_id, current_user, db)
    return KnowledgeBaseService().delete_document(business_id, title)


# ------------------------------------------------------------------ #
# Re-embed everything with the currently active embedding backend
# ------------------------------------------------------------------ #

@router.post("/reindex")
def reindex(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_business(business_id, current_user, db)
    return KnowledgeBaseService().reindex(business_id)


# ------------------------------------------------------------------ #
# Test retrieval directly
# ------------------------------------------------------------------ #

@router.get("/search")
def search(
    business_id: int = Query(...),
    query: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Debug/preview endpoint: shows exactly what the auto-reply agent would
    retrieve from the knowledge base for a given customer question.
    """
    _get_owned_business(business_id, current_user, db)
    return {"results": KnowledgeBaseService().search(business_id, query)}
