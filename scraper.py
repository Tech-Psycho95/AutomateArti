"""
opp-radar: zero-cost opportunity radar.

Checks:
  1. Devpost's public hackathon API for new hackathons matching your keywords.
  2. A list of "watch pages" (fellowship / accelerator / hackathon sites) for
     content changes (new cohort opened, deadline updated, etc.) via hashing.

Sends a Telegram message for anything new. Designed to run on a free
GitHub Actions cron job — no paid infra, no API keys except a free Telegram bot.
"""

import hashlib
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml
from dateutil import parser as date_parser

import calendar_sync
import email_sync

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.yaml"
SEEN_PATH = ROOT / "seen.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

RSS_TOP_10_APT_RE = re.compile(r"\btop\s+10\s+tech\s+apprenticeships\b", re.IGNORECASE)
RSS_NOISE_TITLE_RE = re.compile(
    r"\b(experience|story|stories|wins award|won award|celebrates|celebration|graduation|testimonial|testimonials|award|announces?|announcement|launches?|renews|committed|tops|success|selects?|presented|what(?:'s| is) changing)\b",
    re.IGNORECASE,
)
RSS_OPPORTUNITY_RE = re.compile(
    r"\b(apply|apply now|open|now hiring|applications? open|accepting applications|call for|call for applications|deadline|grant|grants|fellowship|fellowships|hackathon|accelerator|traineeship|traineeships|internship|internships|program|programs|cohort|cohorts|funding)\b",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; opp-radar/1.0; +https://github.com/)"
}


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_seen():
    if SEEN_PATH.exists():
        with open(SEEN_PATH) as f:
            seen = json.load(f)
    else:
        seen = {}
    seen.setdefault("devpost_ids", [])
    seen.setdefault("page_hashes", {})
    seen.setdefault("rss_item_ids", [])
    return seen


def save_seen(seen):
    with open(SEEN_PATH, "w") as f:
        json.dump(seen, f, indent=2)


def escape_html(text):
    return html.escape(str(text or ""), quote=False)


def escape_url(url):
    return html.escape(str(url or ""), quote=True)


def _clean_text(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("No Telegram credentials set — printing instead:\n", text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Telegram messages cap at 4096 chars; chunk if needed.
    for i in range(0, len(text), 4000):
        chunk = text[i:i + 4000]
        resp = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }, timeout=20)
        if resp.status_code != 200:
            print("Telegram send failed:", resp.text)


def telegram_link(url, label="Open link"):
    safe_url = escape_url(url)
    return f'<a href="{safe_url}">{escape_html(label)}</a>'


def parse_deadline(date_range_text):
    """
    Devpost gives deadlines as free text like 'Jun 1, 2026 - Jul 15, 2026'
    or 'Ends August 3, 2026'. Pull out the LAST date found (the actual
    deadline) using fuzzy parsing. Returns a date or None if unparseable.
    """
    if not date_range_text:
        return None

    # Split on common range separators and try the last chunk first,
    # falling back to fuzzy-parsing the whole string.
    chunks = re.split(r"-|–|—|to", date_range_text)
    candidate = chunks[-1].strip() if chunks else date_range_text

    for text in (candidate, date_range_text):
        try:
            parsed = date_parser.parse(text, fuzzy=True, default=datetime(2026, 1, 1))
            if parsed.date() >= date.today():
                return parsed.date()
        except (ValueError, OverflowError):
            continue
    return None


def check_devpost(keywords, seen, calendar_service):
    """Query Devpost's public hackathon search API for each keyword."""
    new_items = []
    for kw in keywords:
        try:
            resp = requests.get(
                "https://devpost.com/api/hackathons",
                params={"search": kw, "status[]": "open", "order_by": "recently-added"},
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[devpost] keyword '{kw}' failed: {e}")
            continue

        for h in data.get("hackathons", []):
            hid = str(h.get("id"))
            if hid in seen["devpost_ids"]:
                continue
            seen["devpost_ids"].append(hid)
            raw_title = h.get("title", "Untitled")
            title = escape_html(raw_title)
            url = h.get("url", "")
            url_markup = telegram_link(url, "View on Devpost") if url else ""
            deadline_text = h.get("submission_period_dates", "unknown deadline")
            prize = escape_html(h.get("prize_amount", ""))
            new_items.append(
                f"🏆 <b>{title}</b>\n"
                f"Deadline: {escape_html(deadline_text)}\n"
                f"{('Prize: ' + prize) if prize else ''}\n"
                f"{url_markup}"
            )

            deadline_date = parse_deadline(deadline_text)
            if deadline_date:
                calendar_sync.add_deadline_event(calendar_service, raw_title, deadline_date, url)
    return new_items


def check_watch_pages(watch_urls, seen):
    """Fetch each watched page and see if its text content changed since last run."""
    new_items = []
    for entry in watch_urls:
        name = entry["name"]
        url = entry["url"]
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            text = re.sub(r"\s+", " ", resp.text)
        except Exception as e:
            print(f"[watch] '{name}' failed: {e}")
            continue

        digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
        prev = seen["page_hashes"].get(url)

        if prev is None:
            # First time seeing this page — record baseline, don't alert.
            seen["page_hashes"][url] = digest
            continue

        if prev != digest:
            seen["page_hashes"][url] = digest
            new_items.append(f"🔔 <b>{escape_html(name)}</b> page changed — check for new updates:\n{telegram_link(url, 'Open page')}")

    return new_items


def _child_element(node, names):
    for child in list(node):
        local_name = child.tag.rsplit("}", 1)[-1]
        if local_name in names:
            return child
    return None


def _xml_text(node):
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def _first_child_text(node, names):
    child = _child_element(node, names)
    if child is not None:
        text = _xml_text(child)
        if text:
            return text
    return ""


def _entry_identity(entry, feed_url):
    for key in ("id", "guid", "link", "url"):
        value = entry.get(key)
        if value:
            return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()
    title = entry.get("title", "")
    return hashlib.sha256(f"{feed_url}|{title}".encode("utf-8")).hexdigest()


def _parse_feed_items(xml_text):
    root = ET.fromstring(xml_text)
    root_name = root.tag.rsplit("}", 1)[-1]

    if root_name == "feed":
        for entry in root.findall("{*}entry"):
            source = _child_element(entry, {"source"})
            yield {
                "title": _first_child_text(entry, {"title"}),
                "link": next((link.get("href") for link in entry.findall("{*}link") if link.get("href")), ""),
                "summary": _first_child_text(entry, {"summary", "content"}),
                "id": _first_child_text(entry, {"id"}),
                "source_title": _xml_text(source),
                "source_url": source.get("url", "") if source is not None else "",
            }
        return

    channel = root.find("channel") or root.find("{*}channel")
    if channel is None:
        return
    for item in channel.findall("item"):
        source = _child_element(item, {"source"})
        yield {
            "title": _first_child_text(item, {"title"}),
            "link": _first_child_text(item, {"link"}),
            "summary": _first_child_text(item, {"description", "encoded"}),
            "id": _first_child_text(item, {"guid"}),
            "source_title": _xml_text(source),
            "source_url": source.get("url", "") if source is not None else "",
        }


def _source_domain(item, feed_url):
    source_url = item.get("source_url") or feed_url
    if not source_url:
        return ""
    parsed = urlparse(source_url)
    return parsed.netloc.lower()


def _rss_item_is_noise(item, feed_url):
    title = _clean_text(item.get("title", ""))
    source_domain = _source_domain(item, feed_url)
    summary = _clean_text(item.get("summary", ""))
    combined = f"{title} {summary}"

    if not title:
        return True

    if RSS_TOP_10_APT_RE.search(title):
        return True

    if source_domain.endswith("nucamp.co"):
        return True

    has_signal = bool(RSS_OPPORTUNITY_RE.search(combined))
    has_noise = bool(RSS_NOISE_TITLE_RE.search(title))

    if has_noise and not has_signal:
        return True

    if not has_signal:
        return True

    return False


def _rss_item_markup(item, feed_name):
    title = escape_html(_clean_text(item.get("title", "")) or feed_name)
    summary = escape_html(_clean_text(item.get("summary", "")))
    link = item.get("link", "")
    source_title = _clean_text(item.get("source_title", ""))

    lines = [f"📰 <b>{title}</b>"]
    if source_title:
        lines.append(f"Source: {escape_html(source_title)}")
    elif feed_name:
        lines.append(f"Source: {escape_html(feed_name)}")
    if summary:
        lines.append(summary)
    if link:
        lines.append(telegram_link(link, "Open item"))
    return "\n".join(lines)


def check_rss_feeds(rss_feeds, seen, max_items_per_run=8):
    new_items = []
    for feed in rss_feeds:
        name = feed.get("name", "RSS feed")
        url = feed.get("url", "")
        if not url:
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            items = list(_parse_feed_items(resp.text))
        except Exception as e:
            print(f"[rss] '{name}' failed: {e}")
            continue

        emitted = 0
        for item in items:
            if emitted >= max_items_per_run:
                break
            if _rss_item_is_noise(item, url):
                continue

            identity = _entry_identity(item, url)
            if identity in seen["rss_item_ids"]:
                continue
            seen["rss_item_ids"].append(identity)
            new_items.append(_rss_item_markup(item, name))
            emitted += 1

    return new_items


def main():
    config = load_config()
    seen = load_seen()
    calendar_service = calendar_sync.get_service()
    max_items_per_run = int(config.get("max_items_per_run", 8) or 8)

    all_new = []
    all_new += check_devpost(config.get("keywords", []), seen, calendar_service)
    all_new += check_rss_feeds(config.get("rss_feeds", []), seen, max_items_per_run=max_items_per_run)
    all_new += check_watch_pages(config.get("watch_urls", []), seen)

    save_seen(seen)

    if all_new:
        header = f"📡 <b>Opp Radar — {len(all_new)} new update(s)</b>\n\n"
        send_telegram(header + "\n\n".join(all_new))
        email_sync.send_email(all_new)
        print(f"Sent {len(all_new)} new item(s).")
    else:
        print("No new items this run.")


if __name__ == "__main__":
    sys.exit(main())
