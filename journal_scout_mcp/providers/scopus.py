from typing import Any, Dict, List, Optional

from ..config import get_api_key
from ..models import Paper
from ..utils import normalize_doi, parse_int, parse_year
from .base import ProviderBase

SCOPUS_BASE = "https://api.elsevier.com/content/"
SCIVAL_BASE = "https://api.elsevier.com/analytics/scival/"
_SCOPUS_ID_PREFIX = "SCOPUS_ID:"
SCIVAL_METRIC_TYPES = "publications,citations,hIndex"


class ScopusProvider(ProviderBase):
    name = "scopus"
    supports_search = True
    supports_citations = True
    supports_author_search = True

    def __init__(self, fetcher, config=None):
        super().__init__(fetcher, config)
        self._api_key = (config or {}).get("api_key")

    def _headers(self):
        key = self._api_key or get_api_key()
        return {
            "X-ELS-APIKey": key,
            "Accept": "application/json",
        }

    @staticmethod
    def _authors(entry) -> List[str]:
        """Collect every author Scopus exposes.

        Search results only carry ``dc:creator`` (first author) while the
        abstract-retrieval endpoint returns the full ``author`` array; read
        whichever is present instead of silently dropping co-authors.
        """
        names: List[str] = []
        raw = entry.get("author") or []
        if isinstance(raw, dict):
            raw = [raw]
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get("authname") or " ".join(
                part for part in [item.get("given-name"), item.get("surname")] if part
            )
            if name:
                names.append(name)
        if not names:
            creator = entry.get("dc:creator")
            if creator:
                names.append(creator)
        return names

    @staticmethod
    def _to_paper(entry):
        scopus_id = entry.get("dc:identifier") or entry.get("eid")
        doi = normalize_doi(entry.get("prism:doi") or entry.get("doi"))
        ids = {}
        if scopus_id:
            ids["scopus"] = scopus_id
        if doi:
            ids["doi"] = doi
        return Paper(
            doi=doi,
            title=entry.get("dc:title") or "",
            abstract=entry.get("dc:description"),
            year=parse_year(entry.get("prism:coverDate") or entry.get("prism:coverDisplayDate")),
            authors=ScopusProvider._authors(entry),
            venue=entry.get("prism:publicationName"),
            citation_count=parse_int(entry.get("citedby-count")),
            url=entry.get("prism:url") or entry.get("link"),
            type=entry.get("subtypeDescription"),
            sources=["scopus"],
            ids=ids,
        )

    @staticmethod
    def _year_clause(query: str, year_from, year_to) -> str:
        """Append Scopus PUBYEAR bounds to a query (shared by every search)."""
        if year_from:
            query = f"{query} AND PUBYEAR > {year_from - 1}"
        if year_to:
            query = f"{query} AND PUBYEAR < {year_to + 1}"
        return query

    async def _search_query(self, query: str, limit: int, offset: int) -> List[Paper]:
        params = {"query": query, "count": limit, "start": offset}
        data = await self._fetch_json(
            f"{SCOPUS_BASE}search/scopus", params=params, headers=self._headers()
        )
        return self._entries_to_papers(data)

    async def search(self, query: str, limit: int, year_from=None, year_to=None, tech_only=False, offset: int = 0) -> List[Paper]:
        if tech_only:
            query = f"({query}) AND SUBJAREA(COMP)"
        return await self._search_query(self._year_clause(query, year_from, year_to), limit, offset)

    async def search_author(self, author: str, limit: int, year_from=None, year_to=None, offset: int = 0) -> List[Paper]:
        query = self._year_clause(f"AU({author})", year_from, year_to)
        return await self._search_query(query, limit, offset)

    @staticmethod
    def _entries_to_papers(data) -> List[Paper]:
        entries = (data.get("search-results") or {}).get("entry") or []
        return [
            ScopusProvider._to_paper(e)
            for e in entries
            if isinstance(e, dict) and "error" not in e
        ]

    @staticmethod
    def _scopus_id(identifier: str) -> str:
        ident = (identifier or "").strip()
        if ident.upper().startswith(_SCOPUS_ID_PREFIX):
            ident = ident[len(_SCOPUS_ID_PREFIX):].strip()
        return ident

    @classmethod
    def _identifier_path(cls, identifier: str) -> Optional[str]:
        ident = cls._scopus_id(identifier)
        if ident.isdigit():
            return f"abstract/scopus_id/{ident}"
        doi = normalize_doi(ident)
        if doi and doi.startswith("10."):
            return f"abstract/doi/{doi}"
        return None

    async def get(self, identifier: str) -> Optional[Paper]:
        path = self._identifier_path(identifier)
        if not path:
            return None
        data = await self._fetch_json(f"{SCOPUS_BASE}{path}", headers=self._headers())
        core = (data.get("abstracts-retrieval-response") or {}).get("coredata") or {}
        return self._to_paper(core) if core else None

    async def citations(self, identifier: str, limit: int) -> List[Paper]:
        sid = self._scopus_id(identifier)
        if not sid.isdigit():
            return []
        data = await self._fetch_json(
            f"{SCOPUS_BASE}search/scopus",
            params={"query": f"REF({sid})", "count": limit},
            headers=self._headers(),
        )
        return self._entries_to_papers(data)

    def _scival_metric_params(self, year_from=None, year_to=None, metric_types: str = SCIVAL_METRIC_TYPES) -> Dict[str, Any]:
        params: Dict[str, Any] = {"metricTypes": metric_types}
        if year_from:
            params["startYear"] = year_from
        if year_to:
            params["endYear"] = year_to
        return params

    async def scival_author_metrics(self, author_id: str, year_from=None, year_to=None) -> Dict[str, Any]:
        return await self._fetch_json(
            f"{SCIVAL_BASE}author/{author_id}/metrics",
            params=self._scival_metric_params(year_from, year_to),
            headers=self._headers(),
        )

    async def scival_institution_metrics(self, institution_id: str, year_from=None, year_to=None) -> Dict[str, Any]:
        return await self._fetch_json(
            f"{SCIVAL_BASE}institution/{institution_id}/metrics",
            params=self._scival_metric_params(year_from, year_to),
            headers=self._headers(),
        )

    async def scival_author_lookup(self, query: str, count: int = 10) -> Dict[str, Any]:
        return await self._fetch_json(
            f"{SCIVAL_BASE}author", params={"query": query, "count": count}, headers=self._headers()
        )

    async def scival_institution_lookup(self, query: str, count: int = 10) -> Dict[str, Any]:
        return await self._fetch_json(
            f"{SCIVAL_BASE}institution", params={"query": query, "count": count}, headers=self._headers()
        )

    async def scival_topic_metrics(self, topic_id: str, year_from=None, year_to=None) -> Dict[str, Any]:
        return await self._fetch_json(
            f"{SCIVAL_BASE}topic/{topic_id}/metrics",
            params=self._scival_metric_params(year_from, year_to, "publications,citations"),
            headers=self._headers(),
        )

    async def get_author(self, author_id: str) -> Dict[str, Any]:
        return await self._fetch_json(
            f"{SCOPUS_BASE}author/author_id/{author_id}", headers=self._headers()
        )

    async def get_quota_status(self) -> Dict[str, Any]:
        return {
            "note": "Elsevier does not expose a quota endpoint. Quota is tracked "
            "via the X-RateLimit-* and X-ELS-Status response headers on actual "
            "API calls; a 429 with QUOTA_EXCEEDED means the weekly quota is spent.",
        }
