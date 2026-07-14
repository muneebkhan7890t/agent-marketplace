from app.ai.agent_brain import AgentBrain
from app.runtime.tool_executor import ToolExecutor
from app.runtime.memory import AgentMemory


class AgentEngine:

    def __init__(self):

        self.brain = AgentBrain()

        self.memory = AgentMemory()

        self.tools = ToolExecutor()

    def run(
        self,
        task
    ):

        tool = self.brain.choose_tool(
            task
        )

        result = self.tools.execute(
            tool
        )

        self.memory.add(
            str(result)
        )

        return {
            "task": task,
            "selected_tool": tool,
            "result": result
        }