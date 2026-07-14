from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def test_job():

    print(
        "Agent executed automatically"
    )

scheduler.add_job(
    test_job,
    "interval",
    minutes=1
)

scheduler.start()