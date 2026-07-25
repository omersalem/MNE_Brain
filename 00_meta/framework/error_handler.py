import logging

logger = logging.getLogger("DiscoveryFramework")

class DiscoveryError(Exception):
    """Base exception for all discovery framework errors."""
    pass

class ConnectionFailureError(DiscoveryError):
    """Raised when network connection to target fails."""
    pass

class AuthenticationError(DiscoveryError):
    """Raised when credentials or tokens are rejected."""
    pass

class PermissionDeniedError(DiscoveryError):
    """Raised when account lacks read permissions for command."""
    pass

class CommandTimeoutError(DiscoveryError):
    """Raised when read query exceeds timeout threshold."""
    pass

class ParsingError(DiscoveryError):
    """Raised when raw telemetry fails normalization."""
    pass

class KnowledgeConflictError(DiscoveryError):
    """Raised when telemetry conflicts with verified manual facts."""
    pass

class FrameworkErrorHandler:
    @staticmethod
    def handle_error(error: Exception, context: str) -> dict:
        error_type = type(error).__name__
        logger.error(f"[{error_type}] during {context}: {str(error)}")
        return {
            "status": "error",
            "error_type": error_type,
            "context": context,
            "message": str(error),
            "recoverable": isinstance(error, (CommandTimeoutError, ParsingError))
        }
