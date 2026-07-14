from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import ForeignKey
from sqlalchemy import String

from app.database import Base


class Purchase(Base):

    __tablename__ = "purchases"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    agent_id = Column(
        Integer,
        ForeignKey("agents.id")
    )

    status = Column(
        String,
        default="paid"
    )