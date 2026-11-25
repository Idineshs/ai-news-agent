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
