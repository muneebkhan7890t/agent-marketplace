from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import ForeignKey
from sqlalchemy import String

from app.database import Base


class InstalledAgent(Base):

    __tablename__ = "installed_agents"

    id = Column(Integer, primary_key=True)

    business_id = Column(
        Integer,
        ForeignKey("businesses.id")
    )

    agent_id = Column(
        Integer,
        ForeignKey("agents.id")
    )

    status = Column(String)