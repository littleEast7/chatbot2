from apscheduler.schedulers.background import BackgroundScheduler


def start_scheduler(config, assistant):
    scheduler = BackgroundScheduler()

    for r in config.get("reminders", []):
        if r["type"] == "interval":
            scheduler.add_job(
                assistant.remind,
                "interval",
                minutes=r["minutes"],
                args=[r["text"]],
            )

    scheduler.start()
    return scheduler
