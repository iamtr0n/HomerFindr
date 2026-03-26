"""APScheduler setup for daily reports and real-time listing alerts."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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

    def _check_search(s):
        """Check a single saved search for new listings and dispatch alerts."""
        import platform
        import subprocess

        from homesearch import database as db
        from homesearch.services.search_service import run_search

        try:
            previous_ids = set(db.get_previous_listing_ids(s.id))
            results = run_search(s.criteria, search_id=s.id)
            new_listings = [l for l in results if l.id and l.id not in previous_ids]

            if not new_listings:
                return

            ns = s.notification_settings

            # Apply coming_soon filter
            if ns.notify_coming_soon_only:
                new_listings = [l for l in new_listings if l.listing_type == "coming_soon"]
                if not new_listings:
                    return

            count = len(new_listings)

            # Desktop notification via osascript (macOS)
            if ns.desktop and platform.system() == "Darwin":
                title = f"HomerFindr: {count} new listing{'s' if count > 1 else ''}"
                body = new_listings[0].address
                if count > 1:
                    body += f" and {count - 1} more"
                body += f" ({s.name})"
                subprocess.run([
                    "osascript", "-e",
                    f'display notification "{body}" with title "{title}" sound name "Glass"'
                ], capture_output=True, timeout=5)

            print(f"[Alerts] {count} new listing(s) for '{s.name}'")

            # Zapier webhook dispatch
            if ns.zapier_webhook:
                import httpx
                try:
                    payload = {
                        "search_name": s.name,
                        "new_count": count,
                        "listing_type": s.criteria.listing_type.value if hasattr(s.criteria.listing_type, 'value') else str(s.criteria.listing_type),
                        "listings": [
                            {
                                "address": l.address,
                                "city": l.city,
                                "state": l.state,
                                "zip_code": l.zip_code,
                                "price": l.price,
                                "beds": l.bedrooms,
                                "baths": l.bathrooms,
                                "sqft": l.sqft,
                                "url": l.source_url,
                                "listing_type": l.listing_type,
                            }
                            for l in new_listings[:10]  # Cap at 10 to avoid huge payloads
                        ],
                    }
                    httpx.post(ns.zapier_webhook, json=payload, timeout=10)
                    print(f"[Alerts] Webhook sent for '{s.name}' ({count} listings)")
                except Exception as e:
                    print(f"[Alerts] Webhook error for '{s.name}': {e}")

        except Exception as e:
            print(f"[Alerts] Error checking '{s.name}': {e}")

    def alert_job():
        """Check active saved searches WITHOUT a webhook (10-min poll)."""
        from homesearch import database as db

        active_searches = db.get_saved_searches(active_only=True)
        if not active_searches:
            return
        for s in active_searches:
            if not s.notification_settings.zapier_webhook:
                _check_search(s)

    def webhook_alert_job():
        """Check active saved searches WITH a webhook configured (3-min poll)."""
        from homesearch import database as db

        active_searches = db.get_saved_searches(active_only=True)
        if not active_searches:
            return
        for s in active_searches:
            if s.notification_settings.zapier_webhook:
                _check_search(s)

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        daily_report_job,
        trigger=CronTrigger(hour=settings.report_hour, minute=settings.report_minute),
        id="daily_report",
        name="Daily HomeSearch Report",
        replace_existing=True,
    )
    _scheduler.add_job(
        alert_job,
        trigger=IntervalTrigger(minutes=10),
        id="realtime_alerts",
        name="Real-time Listing Alerts (10min)",
        replace_existing=True,
    )
    _scheduler.add_job(
        webhook_alert_job,
        trigger=IntervalTrigger(minutes=3),
        id="webhook_alerts",
        name="Webhook Listing Alerts (3min)",
        replace_existing=True,
    )
    _scheduler.start()
    print(f"[Scheduler] Daily report scheduled for {settings.report_hour:02d}:{settings.report_minute:02d}")
    print(f"[Scheduler] Real-time alerts running every 10 minutes (desktop) / 3 minutes (webhook)")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
