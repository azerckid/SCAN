"""HTTPX adapters that perform one JSON-RPC or REST read attempt."""

from datetime import UTC, datetime

import httpx

from scan_tool.domain.source import (
    JsonRpcSourceRequest,
    RestSourceRequest,
    SourceFailure,
    SourceFailureKind,
    SourcePayload,
    SourceRequest,
)

TRANSIENT_HTTP_STATUS_CODES = {500, 502, 503, 504}


class JsonRpcSourceAdapter:
    """One-attempt JSON-RPC adapter with an injected client."""

    def __init__(
        self,
        *,
        source_id: str,
        provider_id: str,
        endpoint: str,
        client: httpx.AsyncClient,
        timeout: httpx.Timeout,
    ) -> None:
        self.source_id = source_id
        self.provider_id = provider_id
        self._endpoint = endpoint
        self._client = client
        self._timeout = timeout

    async def execute(self, request: SourceRequest) -> SourcePayload:
        if not isinstance(request, JsonRpcSourceRequest):
            raise SourceFailure(
                SourceFailureKind.PERMANENT,
                "source adapter does not support this request kind",
            )
        response = await _send(
            self._client,
            "POST",
            self._endpoint,
            timeout=self._timeout,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": request.method,
                "params": request.params,
            },
        )
        try:
            body = response.json()
        except ValueError as error:
            raise SourceFailure(
                SourceFailureKind.INVALID_RESPONSE,
                "source returned malformed JSON",
                status_code=response.status_code,
                raw_bytes=response.content,
            ) from error
        if not isinstance(body, dict) or "error" in body or "result" not in body:
            raise SourceFailure(
                SourceFailureKind.INVALID_RESPONSE,
                "source returned an invalid JSON-RPC response",
                status_code=response.status_code,
                raw_bytes=response.content,
            )
        return _payload(response)


class RestSourceAdapter:
    """One-attempt REST adapter with an injected client."""

    def __init__(
        self,
        *,
        source_id: str,
        provider_id: str,
        base_url: str,
        client: httpx.AsyncClient,
        timeout: httpx.Timeout,
    ) -> None:
        self.source_id = source_id
        self.provider_id = provider_id
        self._base_url = httpx.URL(base_url)
        self._client = client
        self._timeout = timeout

    async def execute(self, request: SourceRequest) -> SourcePayload:
        if not isinstance(request, RestSourceRequest):
            raise SourceFailure(
                SourceFailureKind.PERMANENT,
                "source adapter does not support this request kind",
            )
        url = self._base_url.join(request.path)
        response = await _send(
            self._client,
            request.method,
            str(url),
            timeout=self._timeout,
            params=request.params,
            json=request.json_body,
        )
        return _payload(response, safe_path=request.path)


async def _send(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    timeout: httpx.Timeout,
    params: object = None,
    json: object = None,
) -> httpx.Response:
    try:
        response = await client.request(
            method,
            url,
            timeout=timeout,
            params=params,
            json=json,
        )
    except httpx.TimeoutException as error:
        raise SourceFailure(
            SourceFailureKind.TIMEOUT,
            "source request timed out",
        ) from error
    except httpx.RequestError as error:
        raise SourceFailure(
            SourceFailureKind.UNAVAILABLE,
            "source request failed",
        ) from error

    if response.status_code == 429:
        raise SourceFailure(
            SourceFailureKind.RATE_LIMITED,
            "source rate limit reached",
            status_code=response.status_code,
            retry_after=response.headers.get("Retry-After"),
            raw_bytes=response.content,
        )
    if response.status_code in TRANSIENT_HTTP_STATUS_CODES:
        raise SourceFailure(
            SourceFailureKind.TRANSIENT,
            "source returned a temporary server error",
            status_code=response.status_code,
            raw_bytes=response.content,
        )
    if response.status_code >= 400:
        raise SourceFailure(
            SourceFailureKind.PERMANENT,
            "source rejected the request",
            status_code=response.status_code,
            raw_bytes=response.content,
        )
    return response


def _payload(response: httpx.Response, *, safe_path: str = "/") -> SourcePayload:
    return SourcePayload(
        raw_bytes=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("Content-Type"),
        endpoint_host=response.request.url.host,
        endpoint_path=safe_path,
        retrieved_at=datetime.now(UTC),
    )
