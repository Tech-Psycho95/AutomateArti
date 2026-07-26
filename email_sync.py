"""Gmail SMTP summary email for opp-radar."""

import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GMAIL_TO_ADDRESS = os.environ.get("GMAIL_TO_ADDRESS")


def _build_html_message(items):
    body = [
        "<html><body style='font-family:Arial,Helvetica,sans-serif;line-height:1.5;'>",
        "<h2 style='margin:0 0 12px 0;'>Opp Radar</h2>",
        "<p style='margin:0 0 16px 0;'>New opportunities found in this run:</p>",
        "<ul style='padding-left:20px;margin:0;'>",
    ]

    for item in items:
        body.append(f"<li style='margin:0 0 14px 0;'>{item.replace(chr(10), '<br>')}</li>")

    body.append("</ul>")
    body.append("</body></html>")
    return "".join(body)


def send_email(items):
    if not items:
        return

    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD or not GMAIL_TO_ADDRESS:
        print("No Gmail credentials set — skipping email summary.")
        return

    recipients = [addr.strip() for addr in GMAIL_TO_ADDRESS.split(",") if addr.strip()]
    if not recipients:
        print("No Gmail recipient set — skipping email summary.")
        return

    subject = f"Opp Radar: {len(items)} new opportunities - {date.today().isoformat()}"
    message = MIMEMultipart("alternative")
    message["From"] = GMAIL_ADDRESS
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.attach(MIMEText(_build_html_message(items), "html", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_ADDRESS, recipients, message.as_string())
        print(f"[email] sent summary to {', '.join(recipients)}")
    except Exception as exc:
        print(f"[email] failed: {exc}")