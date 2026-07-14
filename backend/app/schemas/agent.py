from pydantic import BaseModel


class AgentCreate(BaseModel):

    name: str
    description: str
    monthly_price: float
    category: str
    status: str