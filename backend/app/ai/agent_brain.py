from app.ai.huggingface_client import generate_response

from app.ai.prompts import SYSTEM_PROMPT

from app.ai.tool_selector import extract_tool


class AgentBrain:

    def choose_tool(
        self,
        task
    ):

        prompt = f"""
{SYSTEM_PROMPT}

User Task:
{task}
"""

        response = generate_response(prompt)

        return extract_tool(response)