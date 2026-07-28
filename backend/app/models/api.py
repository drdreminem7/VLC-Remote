"""Public API models that contain no VLC implementation details."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

VlcHealthStatus = Literal["online", "unavailable", "not_configured"]


class BackendHealth(BaseModel):
    """Availability and version of the FastAPI process."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["online"] = "online"
    version: str


class VlcHealth(BaseModel):
    """Whether VLC availability has been checked by a configured adapter."""

    model_config = ConfigDict(extra="forbid")

    status: VlcHealthStatus
    reachable: bool
    checked: bool


class HealthResponse(BaseModel):
    """Secret-free response for the public health endpoint."""

    model_config = ConfigDict(extra="forbid")

    backend: BackendHealth
    vlc: VlcHealth
