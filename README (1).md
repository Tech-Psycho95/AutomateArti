# opp-radar

Zero-cost bot that watches for new hackathons and fellowship/accelerator page
changes, pings you on Telegram, and auto-adds detected deadlines to Google
Calendar with reminders. Runs daily on GitHub Actions' free tier.

---

## Setup (~15 minutes, all free)

### 1. Push this folder to a GitHub repo

```bash
cd opp-radar
git init
git add .
git commit -m "opp-radar init"
git remote add origin https://github.com/Tech-Psycho95/opp-radar.git
git branch -M main
git push -u origin main
```
Public repo = unlimited free Actions minutes. Private also works (2000 free
min/month, plenty for this).

### 2. Create a Telegram bot (2 minutes)
1. Message **@BotFather** on Telegram → `/newbot` → follow prompts.
2. Save the **bot token** it gives you.
3. Message your new bot anything (e.g. "hi") so it can message you back.
4. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser,
   find `"chat":{"id": ...}` — that's your **chat ID**.

### 3. Set up Google Calendar sync (5 minutes)
1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create
   a new project (free, no billing needed for this usage level).
2. **APIs & Services → Library** → enable "Google Calendar API".
3. **APIs & Services → Credentials** → Create Credentials → **Service account**
   → give it any name → Create → Done (skip optional steps).
4. Click into the service account → **Keys** tab → Add Key → JSON → download it.
   This file is your `GOOGLE_SERVICE_ACCOUNT_JSON` secret — open it and copy
   the whole raw JSON content.
5. Note the service account's email (looks like
   `something@your-project.iam.gserviceaccount.com`).
6. Open **Google Calendar** in your browser → create a new calendar (or use
   an existing one) called e.g. "Opportunity Deadlines" → Settings → **Share
   with specific people** → paste the service account's email → give it
   **"Make changes to events"** permission.
7. In that calendar's settings, find **Calendar ID** (under "Integrate
   calendar") — that's your `GOOGLE_CALENDAR_ID` secret.

### 4. Add secrets to the repo
GitHub repo → **Settings → Secrets and variables → Actions → New repository
secret**, add all four:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON` (paste the entire JSON file content)
- `GOOGLE_CALENDAR_ID`

### 5. Edit `config.yaml`
Add/remove keywords and watch pages — no code changes needed.

---

## How to run it

### Automatic (the whole point)
Once pushed with secrets set, the GitHub Actions workflow runs by itself
**daily at 08:30 IST**. Nothing to do — new hackathons/page changes hit your
Telegram, deadlines land on your calendar with 3-day, 1-day, and 2-hour
reminders. That's it.

### Run manually right now (to test, or whenever you want a fresh check)
GitHub repo → **Actions** tab → click **"Opp Radar"** in the left sidebar →
**Run workflow** button → Run workflow. Takes ~20 seconds, check your
Telegram after.

### Run it locally on your machine (for debugging)
```bash
git clone https://github.com/Tech-Psycho95/opp-radar.git
cd opp-radar
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export GOOGLE_SERVICE_ACCOUNT_JSON="$(cat path/to/service-account.json)"
export GOOGLE_CALENDAR_ID="your_calendar_id"

python scraper.py
```
Without the env vars set, it just prints what it would have sent instead of
failing — safe to run with zero config to sanity-check the Devpost/watch-page
logic first.

### Change the schedule
Edit the cron line in `.github/workflows/opp-radar.yml`:
```yaml
- cron: "0 3 * * *"   # 03:00 UTC = 08:30 IST, daily
```
Use crontab.guru to build a different schedule (e.g. twice a day during a
heavy application season).

---

## Extending later (still free)
- **More hackathon sources**: Devfolio/Unstop lack clean public APIs — would
  need scraping (more fragile) if Devpost coverage isn't enough.
- **Sharper page-watch alerts**: currently pings on *any* content change to a
  watched page. Can be tightened to only fire when specific keywords (like
  "deadline", "open", "cohort") appear near the diff.
- **Discord** instead of/alongside Telegram: swap `send_telegram()` for a
  webhook POST — same free-tier logic.
