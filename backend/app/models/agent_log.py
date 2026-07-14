from sqlalchemy import Column, String
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.database import Base


from datetime import datetime

from app.database import Base


class AgentLog(Base):

    __tablename__ = "agent_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    business_id = Column(
        Integer,
        ForeignKey("businesses.id")
    )

    agent_id = Column(
        Integer,
        ForeignKey("agents.id")
    )

    input_text = Column(
        Text
    )

    output_text = Column(
        Text
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )



