class TaskManager:

    def create_task(
        self,
        description
    ):

        return {
            "status": "created",
            "task": description
        }