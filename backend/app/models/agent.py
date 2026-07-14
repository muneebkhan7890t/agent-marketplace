from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Numeric

from app.database import Base


class Agent(Base):

    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)

    name = Column(String)

    description = Column(String)

    category = Column(String)

    monthly_price = Column(Numeric)

    status = Column(String)