# Step-by-Step Guide & What Happens Under the Hood

This guide explains **what happens at every stage** of the AI & Tech Morning Digest Agent and gives the **step-by-step process** for running, updating, and syncing the project with GitHub.

---

## Part 1: What Happens When `digest_agent.py` Runs

1. **Load Environment & Secrets (`load_dotenv`)**
   * Reads `GEMINI_API_KEY`, `SENDER_EMAIL`, `APP_PASSWORD`, and `RECIPIENT_EMAIL` from `.env` (locally) or environment variables (in cloud/CI).
   * Keeps secrets out of source control via `.gitignore`.

2. **Fetch & Filter Fresh RSS Articles (`fetch_fresh_items`)**
   * Parses configured RSS/Atom feeds (`O'Reilly Radar`, `The Verge AI`, `TechCrunch AI`) using `feedparser`.
   * Filters out stories older than the `max_age_hours` window (default `30` hours) and skips URLs already stored in `seen_urls.json`.
   * Collects clean `{title, link, snippet}` items up to `limit` (default `15`).
   * Logs a `fetched_items` event to `run_logs.jsonl`. If nothing new is found, it logs `skipped_empty` and exits cleanly.

3. **Summarize with Gemini + Retry & Fallback (`summarize_news`)**
   * Sends the fresh articles to `gemini-3.8-flash` using the `google-genai` SDK with instructions to group key stories into short sections with concise bullets and source links.
   * **Retry on `503` Spikes:** If the model returns a transient `503 UNAVAILABLE` error, it logs `retry_llm` and retries with backoff delays (`3s`, `8s`, `15s`).
   * **Graceful Fallback:** If retries are exhausted or the response is empty, it logs `fallback_digest_used` and builds a clean bulleted fallback digest from the fetched articles so runs still complete.
   * Logs `summarized_items` with input count and output character length.

4. **Deliver Digest to Recipients (`send_email`)**
   * Parses comma-separated addresses from `RECIPIENT_EMAIL` via `get_recipients()`.
   * Connects over `smtplib.SMTP_SSL` to `smtp.gmail.com` on port `465` using `SENDER_EMAIL` and the 16-character Gmail `APP_PASSWORD`.
   * Sends the digest and logs `email_sent` to `run_logs.jsonl`.

5. **Update Deduplication State (`save_seen_urls`)**
   * Adds the newly processed article links to `seen_urls.json` (trimmed to the most recent `2000` entries) and logs `updated_seen_urls` so tomorrow's run won't repeat the same stories.

---