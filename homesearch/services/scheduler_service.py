"""APScheduler setup for daily reports and real-time listing alerts."""

from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from homesearch.config import settings


def _send_web_push(title: str, body: str, url: str = "/") -> None:
    """Send a Web Push notification to all subscribed browsers."""
    from homesearch import database as db
    from homesearch.config import settings

    if not settings.vapid_public_key or not settings.vapid_private_key_path:
        return

    subs = db.get_all_push_subscriptions()
    if not subs:
        return

    try:
        import json
        from pywebpush import webpush, WebPushException

        payload = json.dumps({"title": title, "body": body, "url": url})
        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub["endpoint"],
                        "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                    },
                    data=payload,
                    vapid_private_key=settings.vapid_private_key_path,
                    vapid_claims={"sub": "mailto:homerfindr@localhost"},
                )
            except WebPushException as e:
                if "410" in str(e) or "404" in str(e):
                    # Subscription expired — remove it
                    db.delete_push_subscription(sub["id"])
                else:
                    print(f"[Push] Failed for sub {sub['id'][:8]}: {e}")
    except Exception as e:
        print(f"[Push] Web push error: {e}")


def _shorten_url(url: str) -> str:
    """Shorten a URL via TinyURL (free, no API key). Falls back to original on failure."""
    if not url:
        return url
    try:
        import httpx
        r = httpx.get(f"https://is.gd/create.php?format=simple&url={url}", timeout=5)
        if r.status_code == 200 and r.text.startswith("http"):
            return r.text.strip()
    except Exception:
        pass
    return url


def _format_sms(listing, search_name: str, count: int = 1, alert_type: str = "new") -> str:
    """Build a clean, pre-formatted SMS-ready message for a listing alert."""
    price_str = f"${listing.price:,.0f}" if listing.price else "Price N/A"
    location = ", ".join(p for p in [listing.city, listing.state] if p) or search_name

    if alert_type == "status_change":
        header = f"HomerFindr 🏠\nPending Alert — {search_name}"
    else:
        header = f"HomerFindr 🏠\nNew Listing in {location}"

    url = listing.source_url
    if not url and listing.address:
        query = "+".join(p for p in [listing.address, listing.city, listing.state] if p)
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    url = _shorten_url(url)

    # URL first — survives SMS truncation and Zapier message limits
    lines = [header]
    if url:
        lines.append(f"🔗 {url}")
    lines += ["", f"📍 {listing.address}", f"💰 {price_str}"]

    stats = []
    if listing.bedrooms:
        stats.append(f"🛏 {listing.bedrooms} bd")
    if listing.bathrooms:
        stats.append(f"🛁 {listing.bathrooms:.0f} ba")
    if listing.sqft:
        stats.append(f"📐 {listing.sqft:,} sqft")
    if stats:
        lines.append(" · ".join(stats))

    details = []
    if listing.year_built:
        details.append(f"🏗 Built {listing.year_built}")
    if listing.has_garage:
        details.append("🚗 Garage")
    if listing.has_basement:
        details.append("🏚 Basement")
    if details:
        lines.append(" · ".join(details))

    if count > 1:
        lines.append(f"+ {count - 1} more new listing{'s' if count - 1 != 1 else ''}")

    return "\n".join(lines)


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

        # Daily digest webhook — fires regardless of new listings so you always get a check-in
        webhook_url = settings.zapier_webhook_url
        if webhook_url:
            import httpx
            from homesearch import database as db
            try:
                active_searches = db.get_saved_searches(active_only=True)
                search_names = [s.name for s in active_searches]
                # Count new listings found in the last 24h across all active searches
                conn = db.get_connection()
                try:
                    rows = conn.execute(
                        "SELECT COUNT(*) FROM search_results sr "
                        "JOIN saved_searches ss ON sr.search_id = ss.id "
                        "WHERE sr.is_new = 1 AND sr.found_at >= datetime('now', '-24 hours') "
                        "AND ss.is_active = 1"
                    ).fetchone()
                    new_today = rows[0] if rows else 0
                finally:
                    conn.close()

                if new_today > 0:
                    msg = f"HomerFindr daily summary: {new_today} new listing{'s' if new_today > 1 else ''} found across {len(search_names)} search{'es' if len(search_names) > 1 else ''}."
                else:
                    msg = f"HomerFindr daily check-in: No new listings found in the past 24 hours. {len(search_names)} search{'es' if len(search_names) > 1 else ''} active."

                payload = {
                    "alert_type": "daily_digest",
                    "message": msg,
                    "new_listings_today": new_today,
                    "active_searches": len(search_names),
                    "search_names": search_names,
                }
                httpx.post(webhook_url, json=payload, timeout=10)
                print(f"[Scheduler] Daily digest webhook sent ({new_today} new listings today)")
            except Exception as e:
                print(f"[Scheduler] Daily digest webhook error: {e}")

    def _check_search(s):
        """Check a single saved search for new listings and dispatch alerts."""
        from homesearch import database as db
        from homesearch.services.search_service import run_search

        try:
            # Use only already-alerted (is_new=0) IDs as "previous" so that
            # listings found by manual runs (is_new=1, never alerted) are treated as new here.
            previous_ids = db.get_seen_listing_ids(s.id)

            # Snapshot current listing types before the search to detect status changes
            conn = db.get_connection()
            try:
                prev_types: dict[int, str] = {
                    row["listing_id"]: row["listing_type"]
                    for row in conn.execute(
                        "SELECT sr.listing_id, l.listing_type FROM search_results sr "
                        "JOIN listings l ON l.id = sr.listing_id WHERE sr.search_id = ?",
                        (s.id,),
                    ).fetchall()
                }
            finally:
                conn.close()

            results = run_search(s.criteria, search_id=s.id)
            new_listings = [l for l in results if l.id and l.id not in previous_ids]

            # Detect status changes: listing was previously "sale" and is now "pending"
            status_changed = [
                l for l in results
                if l.id and l.id in prev_types and prev_types[l.id] == "sale" and l.listing_type == "pending"
            ]

            ns = s.notification_settings
            if ns.alerts_paused:
                print(f"[Alerts] Skipping '{s.name}' — alerts paused")
                return

            webhook_url = ns.zapier_webhook or settings.zapier_webhook_url

            # Fire status-change alerts for sale→pending transitions
            if status_changed and webhook_url:
                import httpx
                for l in status_changed:
                    try:
                        payload = {
                            "alert_type": "status_change",
                            "search_name": s.name,
                            "message": _format_sms(l, s.name, alert_type="status_change"),
                            "address": l.address,
                            "city": l.city,
                            "state": l.state,
                            "price": l.price,
                            "days_on_mls": l.days_on_mls,
                            "agent_name": l.agent_name,
                            "agent_phone": l.agent_phone,
                            "agent_email": l.agent_email,
                            "url": l.source_url,
                            "warning": "High chance this sale is not going through — consider reaching out to the agent directly." if (l.days_on_mls or 0) >= 30 else "",
                        }
                        httpx.post(webhook_url, json=payload, timeout=10)
                        print(f"[Alerts] Status-change webhook sent: {l.address} (sale→pending)")
                    except Exception as e:
                        print(f"[Alerts] Status-change webhook error: {e}")

            if not new_listings:
                print(f"[Alerts] Checked '{s.name}' — no new listings")
                return

            # Apply coming_soon filter
            if ns.notify_coming_soon_only:
                new_listings = [l for l in new_listings if l.listing_type == "coming_soon"]
                if not new_listings:
                    return

            count = len(new_listings)

            # Desktop notification (cross-platform via plyer)
            if ns.desktop:
                title = f"HomerFindr: {count} new listing{'s' if count > 1 else ''}"
                body = new_listings[0].address
                if count > 1:
                    body += f" and {count - 1} more"
                body += f" ({s.name})"
                try:
                    from plyer import notification as _notif
                    _notif.notify(
                        title=title,
                        message=body,
                        app_name="HomerFindr",
                        timeout=10,
                    )
                except Exception:
                    pass

            print(f"[Alerts] {count} new listing(s) for '{s.name}'")

            # Zapier webhook dispatch — per-search URL takes precedence, falls back to global
            if webhook_url:
                import httpx
                first = new_listings[0]
                payload = {
                        "alert_type": "new_listings",
                        "search_name": s.name,
                        "new_count": count,
                        # Pre-formatted SMS-ready message — map this field directly to your SMS body in Zapier
                        "message": _format_sms(first, s.name, count=count),
                        "listing_type": s.criteria.listing_type.value if hasattr(s.criteria.listing_type, 'value') else str(s.criteria.listing_type),
                        # Flat fields for the first listing (for simple Zapier email/SMS steps)
                        "address": first.address,
                        "city": first.city,
                        "state": first.state,
                        "price": first.price,
                        "beds": first.bedrooms,
                        "baths": first.bathrooms,
                        "sqft": first.sqft,
                        "url": first.source_url,
                        "recipients": ns.recipients,
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
                                "photo_url": l.photo_url,
                                "listing_type": l.listing_type,
                                "agent_name": l.agent_name,
                                "agent_phone": l.agent_phone,
                            }
                            for l in new_listings[:10]
                        ],
                    }
                try:
                    httpx.post(webhook_url, json=payload, timeout=10)
                    print(f"[Alerts] Webhook sent for '{s.name}' ({count} listings)")
                except Exception as e:
                    print(f"[Alerts] Webhook failed for '{s.name}', queuing for retry: {e}")
                    db.queue_alert(s.id, s.name, webhook_url, payload)

            # Web Push notifications to subscribed browsers/phones
            _send_web_push(
                title=f"HomerFindr: {count} new listing{'s' if count > 1 else ''}",
                body=f"{new_listings[0].address} · {s.name}",
                url=new_listings[0].source_url or "/",
            )

            # Mark alerted listings as seen across ALL searches so the same
            # listing doesn't fire duplicate alerts from overlapping searches.
            db.mark_listings_alerted([l.id for l in new_listings if l.id])

        except Exception as e:
            print(f"[Alerts] Error checking '{s.name}': {e}")

    def alert_job():
        """Check active saved searches that have no webhook (desktop-only, 10-min poll)."""
        from homesearch import database as db

        active_searches = db.get_saved_searches(active_only=True)
        if not active_searches:
            return
        global_webhook = settings.zapier_webhook_url
        for s in active_searches:
            if not s.notification_settings.zapier_webhook and not global_webhook:
                _check_search(s)

    def webhook_alert_job():
        """Check active saved searches that have a webhook (per-search or global, 3-min poll)."""
        from homesearch import database as db

        active_searches = db.get_saved_searches(active_only=True)
        if not active_searches:
            return
        global_webhook = settings.zapier_webhook_url
        for s in active_searches:
            if s.notification_settings.zapier_webhook or global_webhook:
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

    def retry_pending_alerts_job():
        """Retry any webhook alerts that failed during a previous attempt."""
        import httpx
        from homesearch import database as db

        pending = db.get_pending_alerts()
        if not pending:
            return
        for alert in pending:
            if alert["attempts"] >= 10:
                db.mark_alert_sent(alert["id"])
                print(f"[Alerts] Dropping alert for '{alert['search_name']}' after 10 failed attempts")
                continue
            try:
                httpx.post(alert["webhook_url"], json=alert["payload"], timeout=10)
                db.mark_alert_sent(alert["id"])
                print(f"[Alerts] Retry succeeded for '{alert['search_name']}'")
            except Exception as e:
                db.increment_alert_attempts(alert["id"])
                print(f"[Alerts] Retry {alert['attempts'] + 1} failed for '{alert['search_name']}': {e}")

    _scheduler.add_job(
        retry_pending_alerts_job,
        trigger=IntervalTrigger(minutes=5),
        id="retry_pending_alerts",
        name="Retry Failed Webhook Alerts (5min)",
        replace_existing=True,
    )

    # Fire a single webhook check 60s after startup to catch anything missed while server was down
    _scheduler.add_job(
        webhook_alert_job,
        trigger=DateTrigger(run_date=datetime.now() + timedelta(seconds=60)),
        id="startup_catchup",
        name="Startup Catch-up Check",
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


def reschedule_jobs(interval_minutes: int, enabled: bool):
    """Update the polling interval for background alert jobs and pause/resume as needed."""
    global _scheduler
    if _scheduler is None:
        return

    from apscheduler.triggers.interval import IntervalTrigger

    job_ids = ["webhook_alerts", "realtime_alerts"]
    if not enabled:
        for job_id in job_ids:
            try:
                _scheduler.pause_job(job_id)
                print(f"[Scheduler] Paused {job_id}")
            except Exception:
                pass
    else:
        _scheduler.reschedule_job(
            "webhook_alerts",
            trigger=IntervalTrigger(minutes=interval_minutes),
        )
        _scheduler.reschedule_job(
            "realtime_alerts",
            trigger=IntervalTrigger(minutes=max(interval_minutes, 10)),
        )
        for job_id in job_ids:
            try:
                _scheduler.resume_job(job_id)
            except Exception:
                pass
        print(f"[Scheduler] Background polling updated → every {interval_minutes} min")
