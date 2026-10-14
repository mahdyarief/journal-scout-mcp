from typing import List, Optional

from ..config import get_polite_email
from ..models import Paper
from ..utils import first_of, normalize_doi, parse_year, strip_jats
from .base import ProviderBase

CROSSREF_URL = "https://api.crossref.org/works"


class CrossrefProvider(ProviderBase):
    name = "crossref"
    supports_search = True
    supports_author_search = True

    @staticmethod
    def _to_paper(item):
        authors = []
        for a in item.get("author", []) or []:
            name = " ".join(x for x in [a.get("given"), a.get("family")] if x)
            if name:
                authors.append(name)
        year = None
        for key in ("published", "published-print", "published-online"):
            parts = (item.get(key) or {}).get("date-parts") or []
            if parts and parts[0]:
                year = parse_year(parts[0][0])
                break
        doi = normalize_doi(item.get("DOI"))
        return Paper(
            doi=doi,
            title=first_of(item.get("title")) or "",
            abstract=strip_jats(item.get("abstract")),
            year=year,
            authors=authors,
            venue=first_of(item.get("container-title")),
            citation_count=item.get("is-referenced-by-count"),
            url=item.get("URL"),
            type=item.get("type"),
            sources=["crossref"],
            ids={"crossref": item.get("DOI")} if item.get("DOI") else {},
        )

    def _items_to_papers(self, data) -> List[Paper]:
        items = (data.get("message") or {}).get("items") or []
        return [self._to_paper(i) for i in items]

    async def search(self, query: str, limit: int, year_from=None, year_to=None, tech_only=False, offset: int = 0) -> List[Paper]:
        params = {"query": query, "rows": limit, "offset": offset, "mailto": get_polite_email()}
        data = await self._fetch_json(CROSSREF_URL, params=params)
        return self._items_to_papers(data)

    async def search_author(self, author: str, limit: int, year_from=None, year_to=None, offset: int = 0) -> List[Paper]:
        params = {
            "query.author": author,
            "rows": limit,
            "offset": offset,
            "mailto": get_polite_email(),
        }
        data = await self._fetch_json(CROSSREF_URL, params=params)
        return self._items_to_papers(data)

    async def get(self, identifier: str) -> Optional[Paper]:
        doi = normalize_doi(identifier)
        if not doi:
            return None
        data = await self._fetch_json(f"{CROSSREF_URL}/{doi}", params={"mailto": get_polite_email()})
        message = data.get("message")
        return self._to_paper(message) if message else None
