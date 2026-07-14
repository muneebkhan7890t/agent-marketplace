class AgentExecutor:

    def execute(
        self,
        task
    ):

        return {
            "status":"completed",
            "result":f"Executed {task}"
        }