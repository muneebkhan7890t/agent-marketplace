from app.workers.celery_app import celery

@celery.task
def run_agent_task(task):

    print(
        f"Running task: {task}"
    )

    return {
        "status": "completed"
    }