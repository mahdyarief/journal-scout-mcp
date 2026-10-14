# journal-scout-mcp

Multi-source journal research MCP server. Searches Scopus, arXiv, OpenAlex,
Semantic Scholar, Crossref, DBLP, and Unpaywall in parallel, then merges
duplicate results into one entry per paper (DOI-first dedup) and reports
partial failures. Includes SciVal author/institution/topic metrics.

Built as a companion to browser-based scraping: use this server to *find and
verify* papers at scale (metadata, abstracts, open-access links, citation
graphs), then drive a real browser (e.g. FastMCP Browser) only for the pages
that block plain HTTP — WAFs, login walls, JS-heavy publishers.

## Tools (18)

Unified: `search_all`, `search_author`, `get_paper`, `get_citations`.
Per-source: `search_scopus`, `search_arxiv`, `search_openalex`,
`search_semanticscholar`, `search_crossref`, `search_dblp`.
Scopus detail: `get_abstract_details`, `get_author_profile`, `get_quota_status`.
SciVal: `scival_author_metrics`, `scival_institution_metrics`,
`scival_author_lookup`, `scival_institution_lookup`, `scival_topic_metrics`.

Every search accepts `offset` for pagination (uses each API's native
parameter) and `year_from`/`year_to` bounds (native date filters where the
source offers them). `search_author` fans out to every author-search-capable
source — Scopus, Crossref, OpenAlex, arXiv, and Semantic Scholar — then merges
and dedupes the results.

`get_abstract_details` requests the full Scopus view first and falls back to
the metadata-only view when the key lacks the abstract entitlement, so it
degrades to complete metadata instead of erroring on a metadata-only key.

## Prompts

The server also exposes MCP prompt templates (`list_prompts` / `get_prompt`):

- `literature_review` — topic plus optional `year_from`/`year_to`.
- `author_overview` — an author name.
- `citation_trace` — a paper identifier.

Each renders a ready-to-run plan that drives the tools above.

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
  "polite_email": "you@example.com",
  "cache_ttl": 300
}
```

Only the Elsevier `api_key` is required (Scopus/SciVal only). The other
sources work without a key. `polite_email` improves rate limits on OpenAlex,
Crossref, and Unpaywall. `cache_ttl` (seconds, default `300`) serves repeated
queries from an in-memory cache instead of re-hitting the upstream APIs;
set it to `0` to disable caching.

Environment variables override the file:

- `SCOPUS_API_KEY` (or `api_key` in config.json)
- `SEMANTIC_SCHOLAR_API_KEY`
- `JOURNAL_SCOUT_EMAIL` (or `polite_email`)
- `JOURNAL_SCOUT_CACHE_TTL` (or `cache_ttl`)

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
- A shared TTL cache short-circuits duplicate queries per provider, so
  retries and repeated searches do not burn the (limited) upstream quota.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

129 tests covering all providers, the HTTP retry/cache layer, dedup/merge
logic (DOI-first with title/author fallback), pagination, year filters,
author search, prompt templates, and the server tool registry.

## License

MIT — see [LICENSE](LICENSE).