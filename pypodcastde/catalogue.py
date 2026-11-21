"""Types for the fields requested by the ARD show catalogue query."""

from typing import NotRequired, TypedDict


class Audio(TypedDict):
    """One playable audio variant and its optional direct-download URL."""

    url: str
    downloadUrl: NotRequired[str | None]
    mimeType: NotRequired[str | None]


class Episode(TypedDict):
    """Episode metadata used to select, name, and index a download."""

    id: str
    title: str
    publishDate: str
    duration: int | None
    summary: NotRequired[str | None]
    audios: list[Audio] | None


class PageInfo(TypedDict):
    """Cursor and continuation flag for an ARD result page."""

    hasNextPage: bool
    endCursor: str | None


class Items(TypedDict):
    """A page of episodes and the size of the complete catalogue."""

    totalCount: int
    nodes: list[Episode]
    pageInfo: PageInfo


class Show(TypedDict):
    """Show metadata returned for one catalogue request."""

    title: str
    items: Items


class CatalogueData(TypedDict):
    """GraphQL data payload; unknown show IDs return a null show."""

    show: Show | None
