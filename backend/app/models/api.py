"""Public health and error models that contain no secret values."""

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


ErrorCode = Literal[
    "UNAUTHORIZED",
    "INVALID_REQUEST",
    "UNSUPPORTED_OPERATION",
    "VLC_UNAVAILABLE",
    "VLC_AUTHENTICATION_FAILED",
    "VLC_COMMAND_FAILED",
    "INTERNAL_ERROR",
]


class ErrorBody(BaseModel):
    """Stable error information safe to expose to the phone."""

    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str
    retryable: bool
    details: dict[str, object] | None = None


class ErrorResponse(BaseModel):
    """Consistent wrapper used by every API error."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


class RemoteShutdownResponse(BaseModel):
    """Acknowledgement returned before the Mac closes the remote service."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["shutting_down"] = "shutting_down"
