"""Abstract base for all real estate data providers."""

from abc import ABC, abstractmethod

from homesearch.models import Listing, SearchCriteria


class BaseProvider(ABC):
    """Interface that every data source must implement."""

    @abstractmethod
    def search(self, criteria: SearchCriteria) -> list[Listing]:
        """Fetch listings matching the given criteria.

        Providers should do their best to map criteria fields to platform-specific
        filters. Fields the platform doesn't support natively will be filtered
        client-side by the SearchService.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this provider (e.g. 'realtor', 'redfin')."""

    @property
    def enabled(self) -> bool:
        """Override to disable a provider (e.g. missing API key)."""
        return True
