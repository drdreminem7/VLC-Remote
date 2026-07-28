"""FastAPI dependencies with replaceable Phase 1 service stubs."""

from backend.app.services.vlc_client import (
    UnconfiguredVlcClient,
    VlcClientProtocol,
)

_vlc_client: VlcClientProtocol = UnconfiguredVlcClient()


def get_vlc_client() -> VlcClientProtocol:
    """Return the VLC adapter.

    Phase 2 replaces the unconfigured implementation with the authenticated
    HTTPX client. Keeping the dependency behind a protocol prevents the health
    route from learning VLC-specific command details.
    """

    return _vlc_client
