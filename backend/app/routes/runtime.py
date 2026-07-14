from fastapi import APIRouter

from app.runtime.engine import AgentEngine

router = APIRouter()

engine = AgentEngine()


@router.post("/run")
def run_agent(task: str):

    result = engine.run(task)

    return result

