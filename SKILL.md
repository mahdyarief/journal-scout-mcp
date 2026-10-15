---
name: journal-scout-mcp-user
description: Use when using the journal-scout MCP for research.
---
# Journal Scout MCP User Guide

This skill explains how to install, configure, and use the `journal-scout-mcp` MCP server.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mahdyarief/journal-scout-mcp.git
   cd journal-scout-mcp
   ```
2. Create a virtual environment and install:
   ```bash
   python -m venv .venv
   .venv\Scripts\pip install -e .  # Windows
   # or
   source .venv/bin/pip install -e .  # Unix
   ```
3. Copy `config.json.example` to `config.json` and fill in your Elsevier API key (required for Scopus/SciVal tools).

## Configuration

The `config.json` file (git-ignored) should contain:
```json
{
  "api_key": "YOUR_ELSEVIER_API_KEY",
  "semantic_scholar_api_key": "",
  "polite_email": "you@example.com",
  "cache_ttl": 300
}
```
- `api_key`: Required for Scopus and SciVal tools (free tier available).
- `semantic_scholar_api_key`: Optional, for higher rate limits.
- `polite_email`: Used by OpenAlex, Crossref, and Unpaywall to improve rate limits.
- `cache_ttl`: Seconds to cache API responses (default 300). Set to 0 to disable.

## Running the MCP Server

Start the server with:
```bash
python -m journal_scout_mcp.server
```

Or via the installed console script:
```bash
journal-scout-mcp
```

## Available Tools

The server provides 18 tools for searching and retrieving journal metadata:

### Unified Search
- `search_all`: Search all sources in parallel, merge duplicates.
- `search_author`: Search for authors across sources (Scopus, Crossref, OpenAlex, arXiv, Semantic Scholar).
- `get_paper`: Resolve a DOI/arXiv/Scopus/OpenAlex ID across sources.
- `get_citations`: Collect cross-source citation graph (Scopus + OpenAlex).

### Per-Source Search
- `search_scopus`, `search_arxiv`, `search_openalex`, `search_semanticscholar`, `search_crossref`, `search_dblp` (Unpaywall hanya diakses via `get_paper` / DOI, tidak menyediakan tool search tersendiri).

### Scopus Detail Tools
- `get_abstract_details`: Get abstract and metadata for a Scopus ID. Tries `view=FULL` first, falls back to metadata-only view if the key lacks entitlement.
- `get_author_profile`: Get author profile (h-index, document count, etc.).
- `get_quota_status`: Check remaining API quota for the day.

### SciVal Tools
- `scival_author_metrics`, `scival_author_lookup`
- `scival_institution_metrics`, `scival_institution_lookup`
- `scival_topic_metrics`

## MCP Prompts

The server also exposes three prompt templates:

- `literature_review`: Generate a literature review plan on a topic, optional year bounds.
- `author_overview`: Generate an author overview plan.
- `citation_trace`: Generate a citation tracing plan for a paper.

Use via:
- `list_prompts` to see available prompts.
- `get_prompt` with prompt name and arguments to get the rendered plan.

## Usage Examples

### Search for a paper by DOI

```python
# Pseudocode for MCP client
result = await mcp.call_tool(
    "journal-scout",
    "get_paper",
    {"identifier": "10.1109/5.771073"}
)
```

### Search for articles by author

```python
result = await mcp.call_tool(
    "journal-scout",
    "search_author",
    {"author": "Geoffrey Hinton", "year_from": 2010, "year_to": 2020}
)
```

### Get abstract (with graceful degradation)

```python
result = await mcp.call_tool(
    "journal-scout",
    "get_abstract_details",
    {"scopus_id": "105048092271"}
)
# If your key lacks abstract entitlement, you still get metadata.
```

### Use a prompt

```python
prompt = await mcp.call_tool(
    "journal-scout",
    "get_prompt",
    {
        "name": "literature_review",
        "arguments": {
            "topic": "transformer architectures",
            "year_from": "2018",
            "year_to": "2023"
        }
    }
)
print(prompt.content)
```

## Notes

- The `get_abstract_details` tool now degrades gracefully: if your API key does not include entitlement to the abstract (`view=FULL`), it returns complete metadata instead of erroring.
- Author search works across five sources: Scopus, Crossref, OpenAlex, arXiv, and Semantic Scholar.
- All tools support pagination via `offset` where applicable.
- The server includes retry logic for HTTP 429, 406 (arXiv), and non-JSON responses (bot challenges).

## Troubleshooting

- **Tool returns `abstract=null` or empty**: Your Elsevier key likely lacks entitlement to fetch abstracts. The tool is working correctly—it returns metadata and will return the abstract if you upgrade your key.
- **Rate limit errors (429)**: Increase `polite_email` (for OpenAlex/Crossref/Unpaywall) or wait; the server includes retry and caching.
- **SSL certificate issues**: Ensure your system's CA certificates are up to date, especially in corporate environments.

---
