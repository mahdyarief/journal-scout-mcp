import json
from pathlib import Path

import httpx

from journal_scout_mcp.providers.crossref import CrossrefProvider

FIXTURES = Path(__file__).parent.parent / "fixtures"


async def test_search_maps_items_to_paper(monkeypatch):
    payload = json.loads((FIXTURES / "crossref_search.json").read_text(encoding="utf-8"))

    def handler(request):
        return httpx.Response(200, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = CrossrefProvider(client)
    try:
        papers = await provider.search("long short-term memory", 5)
        assert len(papers) == 1
        p = papers[0]
        assert p.doi == "10.1162/neco.1997.9.8.1735"
        assert p.title == "Long Short-Term Memory"
        assert p.authors == ["Sepp Hochreiter", "Jürgen Schmidhuber"]
        assert p.venue == "Neural Computation"
        assert p.year == 1997
        assert p.citation_count == 42000
        assert p.abstract == "We propose LSTM."
        assert p.sources == ["crossref"]
        assert p.ids["crossref"] == "10.1162/neco.1997.9.8.1735"
    finally:
        await client.aclose()


async def test_search_sends_offset_for_pagination():
    captured = {}

    def handler(request):
        captured["offset"] = request.url.params.get("offset")
        return httpx.Response(200, json={"message": {"items": []}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = CrossrefProvider(client)
    try:
        await provider.search("lstm", 10, offset=15)
        assert captured["offset"] == "15"
    finally:
        await client.aclose()


async def test_search_author_sends_query_author():
    captured = {}

    def handler(request):
        captured["query.author"] = request.url.params.get("query.author")
        return httpx.Response(200, json={"message": {"items": []}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = CrossrefProvider(client)
    try:
        await provider.search_author("Vaswani", 5)
        assert captured["query.author"] == "Vaswani"
    finally:
        await client.aclose()