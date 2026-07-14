from app.ai.agent_brain import AgentBrain

brain = AgentBrain()

tool = brain.choose_tool(
    "Check today's orders"
)

print(tool)