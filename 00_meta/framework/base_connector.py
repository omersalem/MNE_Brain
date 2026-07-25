from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseConnector(ABC):
    """Abstract Base Class for all Ministry Infrastructure Discovery Connectors."""

    def __init__(self, connector_name: str, vendor: str):
        self.connector_name = connector_name
        self.vendor = vendor

    @abstractmethod
    def validate_connection(self, profile: Dict[str, Any]) -> bool:
        """Stage 1: Verify network reachability."""
        pass

    @abstractmethod
    def test_authentication(self, profile: Dict[str, Any]) -> bool:
        """Stage 2: Verify read-only credentials."""
        pass

    @abstractmethod
    def detect_capabilities(self, profile: Dict[str, Any]) -> List[str]:
        """Stage 3: Query OS version & feature capabilities."""
        pass

    @abstractmethod
    def collect_raw_telemetry(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4: Execute non-destructive read queries."""
        pass

    @abstractmethod
    def normalize_data(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 6: Convert raw telemetry to standard Ministry schema."""
        pass
