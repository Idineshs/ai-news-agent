# AI & Tech Morning Digest Agent

An automated Python briefing agent built with a **Prompt Chaining** workflow. It aggregates recent AI and technology articles from curated RSS feeds, deduplicates previously sent stories, summarizes the top highlights using Google Gemini (`gemini-3.8-flash`), and delivers a scannable morning digest via email to one or more recipients.

## Architecture & Workflow

1. **Ingestion & Filtering (`fetch_fresh_items`):** Parses RSS/Atom feeds (`O'Reilly Radar`, `The Verge AI`, `TechCrunch AI`), filters out articles older than 30 hours, and skips links already recorded in `seen_urls.json`.
2. **LLM Summarization with Resilience (`summarize_news`):** Sends the filtered articles to `gemini-3.8-flash` to synthesize 6–8 key takeaways grouped by topic. Includes exponential backoff retries for transient `503` server demand spikes and an automatic bulleted fallback digest if the API remains unreachable.
3. **Multi-Recipient Delivery (`send_email`):** Sends the formatted briefing over SMTP SSL (`smtp.gmail.com`) to one or more comma-separated recipients (with optional `Bcc` support).
4. **State & Observability (`log_step`, `save_seen_urls`):** Appends structured JSON events (`fetched_items`, `retry_llm`, `summarized_items`, `email_sent`) to `run_logs.jsonl` and persists sent URLs in `seen_urls.json`.

## Project Structure

```text
ai_news-agent/
├── digest_agent.py      # Main pipeline script
├── requirements.txt     # Python dependencies
├── .env.example         # Template for required environment variables
├── .gitignore           # Excludes .env, .venv, logs, and state files
└── README.md            # Project documentation

## How to Get a 16-Character Google App Password (`APP_PASSWORD`)

Gmail requires a 16-character **App Password** (rather than your regular Gmail login password) when sending mail via SMTP (`smtp.gmail.com`) with 2-Step Verification enabled.

1. **Enable 2-Step Verification on Your Google Account**
   * Go to your [Google Account](https://myaccount.google.com/) and open **Security**.
   * Under **How you sign in to Google**, select **2-Step Verification** and follow the prompts to turn it on if it is not already active.

2. **Open App Passwords**
   * Visit [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (or search for **App passwords** inside your Google Account settings).

3. **Create an App Password**
   * Enter a descriptive **App name** (for example, `AI News Digest Agent`).
   * Click **Create**.

4. **Copy the 16-Character Code**
   * Google will display a 16-character password (often shown in four groups of four characters, such as `abcd efgh ijkl mnop`).
   * Copy the code and paste it into your `.env` file as `APP_PASSWORD` (with or without spaces—most setups work cleanly without spaces, e.g., `APP_PASSWORD=abcdefghijklmnop`).
   * Click **Done** (note that Google will not show the code again once you leave the screen).