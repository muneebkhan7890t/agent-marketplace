from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.jwt_handler import verify_token
from app.models.user import User

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    print("Authorization Header:", credentials.credentials)

    token = credentials.credentials

    payload = verify_token(token)

    print("Payload:", payload)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = db.query(User).filter(
        User.id == payload["user_id"]
    ).first()

    print("User:", user)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user)
):
    """
    Gates the /admin/agents catalog-management endpoints. Requires
    users.is_admin -- see migrate_add_admin_field.py for existing DBs.
    """
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user