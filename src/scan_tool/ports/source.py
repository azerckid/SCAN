"""Source adapter port used by retry and fallback orchestration."""

from typing import Protocol

from scan_tool.domain.source import SourcePayload, SourceRequest


class SourceAdapter(Protocol):
    source_id: str
    provider_id: str

    async def execute(self, request: SourceRequest) -> SourcePayload:
        """Perform exactly one read attempt without retry or fallback."""
        ...
