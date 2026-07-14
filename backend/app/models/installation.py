from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey

from app.database import Base


class AgentInstallation(Base):

    __tablename__ = "agent_installations"

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
        default="installed"
    )

    integration = Column(
        String
    )