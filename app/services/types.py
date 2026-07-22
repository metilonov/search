class SearchServiceError(RuntimeError):
    """Base error for search services."""


class TemporaryServiceError(SearchServiceError):
    """Temporary error from remote service."""
