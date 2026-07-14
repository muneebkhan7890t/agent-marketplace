from pydantic import BaseModel

class AgentCreate(BaseModel):

    name: str

    description: str

    category: str

    monthly_price: float

    status: str