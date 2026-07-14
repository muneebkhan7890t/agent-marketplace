from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey

from app.database import Base


class MCPConnection(Base):

    __tablename__ = "mcp_connections"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    business_id = Column(
        Integer,
        ForeignKey("businesses.id")
    )

    service_name = Column(String)

    access_token = Column(String)

    refresh_token = Column(String)

    account_email = Column(String)

    status = Column(String)