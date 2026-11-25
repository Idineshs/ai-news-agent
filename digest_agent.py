import json
import os
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

RSS_FEEDS = [
    "https://feeds.feedburner.com/oreilly/radar/atom",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
]


def load_seen_urls(path="seen_urls.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_seen_urls(seen_set, path="seen_urls.json"):
    trimmed = list(seen_set)[-2000:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, indent=2)


def log_step(event: str, details: dict, log_path="run_logs.jsonl"):
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **details,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def fetch_fresh_items(max_age_hours=30, limit=15):
    seen = load_seen_urls()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    fresh = []

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            link = entry.get("link")
            title = entry.get("title", "").strip()
            if not link or not title or link in seen:
                continue

            published_dt = None
            if getattr(entry, "published_parsed", None):
                published_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            if published_dt and published_dt < cutoff:
                continue

            summary = entry.get("summary", "").strip()
            fresh.append({
                "title": title,
                "link": link,
                "snippet": summary[:400],
            })
            if len(fresh) >= limit:
                return fresh

    return fresh


def _fallback_digest(items: list[dict]) -> str:
    lines = [
        "Morning AI & Tech Digest (Fallback — LLM temporarily unavailable)",
        "",
    ]
    for item in items[:8]:
        lines.append(f"- {item['title']}")
        lines.append(f"  {item['link']}")
    return "\n".join(lines)


def summarize_news(items: list[dict]) -> str:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    prompt = f"""
You are a concise morning tech & AI briefing assistant.
Using ONLY the articles below, create a clean morning email digest of the top 6–8 most important AI and technology items.

Rules:
- Do not invent facts or links not present in the input.
- Group items into short sections (e.g., "AI Models & Research", "Developer & Industry News").
- For each item, write 1–2 crisp bullet points explaining why it matters, followed by the source link.
- Keep the tone clear, practical, and scannable for a morning read.

Articles:
{json.dumps(items, indent=2)}
"""

    delays = [3, 8, 15]
    last_err = None

    for attempt, delay in enumerate(delays + [None], start=1):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                ),
            )
            if response.text and response.text.strip():
                return response.text
            return _fallback_digest(items)
        except errors.ServerError as e:
            last_err = e
            if delay is None:
                break
            log_step(
                "retry_llm",
                {"attempt": attempt, "sleep_seconds": delay, "error": str(e)},
            )
            time.sleep(delay)

    log_step("fallback_digest_used", {"error": str(last_err)})
    return _fallback_digest(items)


def get_recipients() -> list[str]:
    raw = os.environ.get("RECIPIENT_EMAIL", "")
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def send_email(subject: str, body_text: str, use_bcc: bool = False):
    sender = os.environ["SENDER_EMAIL"]
    password = os.environ["APP_PASSWORD"]
    recipients = get_recipients()

    if not recipients:
        raise ValueError("No valid email addresses found in RECIPIENT_EMAIL.")

    msg = MIMEMultipart()
    msg["From"] = sender
    if use_bcc:
        msg["To"] = sender
        msg["Bcc"] = ", ".join(recipients)
    else:
        msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())


def main():
    items = fetch_fresh_items(max_age_hours=30, limit=15)
    log_step("fetched_items", {"count": len(items)})

    if not items:
        log_step("skipped_empty", {"reason": "No new articles in window"})
        return

    digest = summarize_news(items)
    log_step(
        "summarized_items",
        {"input_count": len(items), "output_chars": len(digest)},
    )

    recipients = get_recipients()
    today_str = datetime.now().strftime("%b %d, %Y")
    send_email(f"Morning AI & Tech Digest — {today_str}", digest, use_bcc=False)
    log_step("email_sent", {"recipients": recipients})

    seen = load_seen_urls()
    seen.update(item["link"] for item in items)
    save_seen_urls(seen)
    log_step("updated_seen_urls", {"total_tracked": len(seen)})


if __name__ == "__main__":
    main()
###just for testing by dinesh