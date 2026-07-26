# Opp Radar

Opp Radar is a zero-cost opportunity tracker that watches for new hackathons,
fellowships, accelerators, and related updates. It checks Devpost listings,
monitors configured web pages for content changes, and sends alerts through
Telegram. Optional Gmail and Google Calendar integrations are included for
summary emails and deadline reminders.

## What It Does

- Searches Devpost for new hackathons that match your keywords.
- Monitors configured pages for changes using content hashing.
- Scans public RSS/Atom feeds for new opportunity announcements.
- Sends new results to Telegram.
- Optionally emails a summary through Gmail.
- Optionally creates Google Calendar deadline events with reminders.

## Tech Stack

- Python 3.11+
- `requests` for HTTP calls
- `PyYAML` for config loading
- `python-dateutil` for deadline parsing
- `google-api-python-client` and `google-auth` for Google Calendar sync
- GitHub Actions for scheduled automation
- Telegram Bot API for notifications
- Gmail SMTP for email summaries

## Project Structure

- `scraper.py` - main entry point that runs Devpost, RSS, and page-change checks.
- `calendar_sync.py` - Google Calendar integration.
- `email_sync.py` - Gmail summary email integration.
- `config.yaml` - editable keywords, watch URLs, and RSS feeds.
- `seen.json` - local state used to avoid duplicate alerts.
- `.github/workflows/opp-radar.yml` - scheduled GitHub Actions workflow.

## Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Add your secrets in GitHub repository settings if you plan to run it in Actions.

Example local setup:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scraper.py
```

## Configuration

Edit `config.yaml` to change what the bot watches.

### Keywords

These are used to search Devpost hackathons.

### Watch URLs

Add any fellowship, accelerator, or hackathon page you want to monitor for
content changes.

### RSS Feeds

Add public RSS or Atom feeds that post opportunity-related announcements.

## Environment Variables

The project works without secrets, but integrations need these values:

- `TELEGRAM_BOT_TOKEN` - Telegram bot token.
- `TELEGRAM_CHAT_ID` - Chat ID that should receive alerts.
- `GMAIL_ADDRESS` - Gmail account used to send summary emails.
- `GMAIL_APP_PASSWORD` - Gmail app password.
- `GMAIL_TO_ADDRESS` - One or more recipient email addresses.
- `GOOGLE_SERVICE_ACCOUNT_JSON` - Raw service account JSON for Calendar API.
- `GOOGLE_CALENDAR_ID` - Calendar ID where deadline events should be created.

## How It Runs

The workflow is designed to run daily on GitHub Actions. On each run it:

1. Loads the current config and previously seen items.
2. Checks Devpost for new matching hackathons.
3. Checks RSS feeds for new opportunity items.
4. Hashes watch pages and alerts when content changes.
5. Saves updated state back to `seen.json`.
6. Sends Telegram alerts, then optional email and calendar updates.

## Notes

- `seen.json` stores deduplication state between runs.
- If credentials are missing, the related integrations are skipped safely.
- The repo is intended to run with no paid infrastructure.
