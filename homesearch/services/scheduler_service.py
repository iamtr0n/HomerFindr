"""APScheduler setup for daily reports."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from homesearch.config import settings


_scheduler: BackgroundScheduler | None = None


def start_scheduler():
    """Start the background scheduler for daily reports."""
    global _scheduler

    if _scheduler is not None:
        return

    from homesearch.services.report_service import generate_report, send_email_report

    def daily_report_job():
        print(f"[Scheduler] Running daily report...")
        try:
            data = generate_report()
            total_new = sum(len(d["new_listings"]) for d in data.values())
            print(f"[Scheduler] Found {total_new} new listings across {len(data)} searches")
            send_email_report(data)
        except Exception as e:
            print(f"[Scheduler] Error in daily report: {e}")

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        daily_report_job,
        trigger=CronTrigger(hour=settings.report_hour, minute=settings.report_minute),
        id="daily_report",
        name="Daily HomeSearch Report",
        replace_existing=True,
    )
    _scheduler.start()
    print(f"[Scheduler] Daily report scheduled for {settings.report_hour:02d}:{settings.report_minute:02d}")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
