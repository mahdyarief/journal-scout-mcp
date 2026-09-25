# journal-scout-mcp

Multi-source journal research MCP server. Searches Scopus, arXiv, OpenAlex,
Semantic Scholar, Crossref, DBLP, and Unpaywall in parallel, then merges
duplicate results into one entry per paper (DOI-first dedup) and reports
partial failures. Includes SciVal author/institution/topic metrics.

Built as a companion to browser-based scraping: use this server to *find and
verify* papers at scale (metadata, abstracts, open-access links, citation
graphs), then drive a real browser (e.g. FastMCP Browser) only for the pages
that block plain HTTP — WAFs, login walls, JS-heavy publishers.

## Tools (17)

Unified: `search_all`, `get_paper`, `get_citations`.
Per-source: `search_scopus`, `search_arxiv`, `search_openalex`,
`search_semanticscholar`, `search_crossref`, `search_dblp`.
Scopus detail: `get_abstract_details`, `get_author_profile`, `get_quota_status`.
SciVal: `scival_author_metrics`, `scival_institution_metrics`,
`scival_author_lookup`, `scival_institution_lookup`, `scival_topic_metrics`.

## Requirements

- Python 3.10+
- An Elsevier/Scopus API key for Scopus/SciVal tools (free tier available
  under 5,000 requests/year); all other sources are keyless.

## Install

```bash
git clone https://github.com/mahdyarief/journal-scout-mcp.git
cd journal-scout-mcp
python -m venv .venv
.venv/bin/pip install -e .
```

On Windows the venv interpreter is `.venv\Scripts\python.exe`.

## Config

Copy `config.json.example` to `config.json`:

```json
{
  "api_key": "YOUR_ELSEVIER_API_KEY",
  "semantic_scholar_api_key": "",
  "polite_email": "you@example.com"
}
```

Only the Elsevier `api_key` is required (Scopus/SciVal only). The other
sources work without a key. `polite_email` improves rate limits on OpenAlex,
Crossref, and Unpaywall.

Environment variables override the file:

- `SCOPUS_API_KEY` (or `api_key` in config.json)
- `SEMANTIC_SCHOLAR_API_KEY`
- `JOURNAL_SCOUT_EMAIL` (or `polite_email`)

`config.json` is intentionally git-ignored — never commit your real keys.

## Run as an MCP server

```bash
python -m journal_scout_mcp.server
```

Or via the installed console script: `journal-scout-mcp`.

### Register in Hermes Agent

Add to your profile `config.yaml` under `mcp_servers`:

```yaml
mcp_servers:
  journal-scout:
    command: D:/path/to/journal-scout-mcp/.venv/Scripts/python.exe
    args: ["-m", "journal_scout_mcp.server"]
    env:
      JOURNAL_SCOUT_EMAIL: "you@example.com"
```

### Register in Claude Desktop / Claude Code

Point the client at the module:

```json
{
  "mcpServers": {
    "journal-scout": {
      "command": "<venv-python>",
      "args": ["-m", "journal_scout_mcp.server"]
    }
  }
}
```

## Rate-limit handling

- Retries on HTTP 429 for all providers.
- Retries on HTTP 406 for arXiv, which signals its per-IP rate limit with
  406 instead of 429.
- Non-JSON (HTML bot-challenge) responses raise a `ProviderError` naming the
  provider and showing the HTML prefix, instead of a confusing JSON parse
  error.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

74 tests covering all providers, the HTTP retry layer, dedup/merge logic,
and the server tool registry.

## License

MIT — see [LICENSE](LICENSE).