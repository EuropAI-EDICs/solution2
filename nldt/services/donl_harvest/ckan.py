"""CKAN Action API client for data.overheid.nl."""

from __future__ import annotations

from typing import Any

import httpx

CKAN_ACTION_BASE = "https://data.overheid.nl/data/api/3/action"
DEFAULT_TIMEOUT = 60.0


class CkanClient:
    """Thin wrapper around DONL CKAN Action API."""

    def __init__(
        self,
        *,
        base_url: str = CKAN_ACTION_BASE,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client
        self._owns_client = client is None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout, follow_redirects=True)
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> CkanClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def action(self, name: str, **params: Any) -> Any:
        url = f"{self.base_url}/{name}"
        resp = self._get_client().get(url, params=params)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise RuntimeError(f"CKAN {name} failed: {body.get('error')}")
        return body["result"]

    def package_search(
        self,
        *,
        q: str = "*:*",
        fq: str | None = None,
        rows: int = 100,
        start: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"q": q, "rows": rows, "start": start}
        if fq:
            params["fq"] = fq
        return self.action("package_search", **params)

    def package_show(self, package_id: str) -> dict[str, Any]:
        return self.action("package_show", id=package_id)

    def iter_packages(
        self,
        *,
        q: str = "*:*",
        fq: str | None = None,
        rows: int = 100,
        max_results: int | None = None,
    ):
        start = 0
        seen = 0
        while True:
            page = self.package_search(q=q, fq=fq, rows=rows, start=start)
            results = page.get("results") or []
            if not results:
                break
            for pkg in results:
                yield pkg
                seen += 1
                if max_results is not None and seen >= max_results:
                    return
            start += len(results)
            if start >= int(page.get("count") or 0):
                break
