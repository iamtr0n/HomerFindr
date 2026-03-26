# 🏠 HomerFindr

Find homes across **Realtor.com, Redfin, and more** — all in one place, on your Mac.

No more juggling tabs. Set your filters once, get alerts when new listings hit.

---

## Install (one command)

Open **Terminal** and paste this:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/iamtr0n/HomerFindr/main/install.sh)"
```

That's it. HomerFindr will:
- ✅ Check and install Python, Node.js, and Git if missing
- ✅ Build the web dashboard
- ✅ Start automatically every time you log in
- ✅ Open in your browser at **http://127.0.0.1:8000**

---

## What You Get

| Feature | Details |
|---------|---------|
| 🔍 Search | Realtor.com + Redfin in one search |
| 🌐 Web dashboard | Clean, Zillow-style UI at localhost:8000 |
| 💻 CLI | Arrow-key wizard, no typing required |
| 📱 SMS alerts | Get texted when new homes hit (free via Zapier) |
| ⭐ Smart scoring | Gold star listings that match everything |
| 🏘️ Multi-city | Search multiple cities/ZIP codes at once |
| 🚗 Highway filter | Avoid listings near major roads |
| 🏫 School ratings | Filter by school district quality |
| 🔔 Real-time alerts | Desktop notifications every 3–10 minutes |

---

## After Installing

```
Open browser  →  http://127.0.0.1:8000
CLI search    →  homesearch search
View logs     →  tail -f /tmp/homerfindr.log
Stop          →  launchctl unload ~/Library/LaunchAgents/com.homerfindr.plist
```

---

## SMS Alerts (optional, free)

The installer will walk you through setting up SMS alerts via Zapier — takes about 3 minutes and uses a free account.

---

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3.11+ · Node.js · Git

Missing any? The installer offers to install them automatically.
