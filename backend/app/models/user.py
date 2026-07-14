from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy.sql import func

from app.database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    full_name = Column(String)

    email = Column(String, unique=True)

    password_hash = Column(String)

    # Gates access to the /admin/agents catalog-management endpoints.
    # Added via migrate_add_admin_field.py for existing databases.
    is_admin = Column(Boolean, default=False)

    created_at = Column(
        DateTime,
        server_default=func.now()
    )