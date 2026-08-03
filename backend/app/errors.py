"""Application-specific exceptions and safe FastAPI error handlers."""

from dataclasses import dataclass

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.models.api import ErrorBody, ErrorCode, ErrorResponse


@dataclass(slots=True)
class ApiException(Exception):
    """An error whose public representation is explicitly controlled."""

    status_code: int
    code: ErrorCode
    message: str
    retryable: bool = False
    details: dict[str, object] | None = None
    headers: dict[str, str] | None = None


class VlcError(Exception):
    """Base class for failures at the VLC boundary."""


class VlcUnavailable(VlcError):
    """VLC could not be reached."""


class VlcAuthenticationFailed(VlcError):
    """VLC rejected its server-side HTTP credentials."""


class VlcCommandFailed(VlcError):
    """VLC returned an invalid or unsuccessful command response."""


class VlcUnsupportedOperation(VlcError):
    """The installed compatibility profile does not support an operation."""


class OpenSubtitlesError(Exception):
    """Base class for failures at the OpenSubtitles boundary."""


class OpenSubtitlesNotConfigured(OpenSubtitlesError):
    """The Mac-only account credentials have not been configured."""


class OpenSubtitlesAuthenticationFailed(OpenSubtitlesError):
    """OpenSubtitles rejected the Mac-only account credentials."""


class OpenSubtitlesUnavailable(OpenSubtitlesError):
    """OpenSubtitles could not be reached or returned an unusable response."""


def error_response(exception: ApiException) -> JSONResponse:
    """Build the standard JSON error envelope."""

    payload = ErrorResponse(
        error=ErrorBody(
            code=exception.code,
            message=exception.message,
            retryable=exception.retryable,
            details=exception.details,
        )
    )
    return JSONResponse(
        status_code=exception.status_code,
        content=payload.model_dump(mode="json"),
        headers=exception.headers,
    )


async def api_exception_handler(
    _request: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, ApiException):  # pragma: no cover - registration guard
        raise exception
    return error_response(exception)


async def validation_exception_handler(
    _request: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(
        exception, RequestValidationError
    ):  # pragma: no cover - registration guard
        raise exception
    fields = [
        {
            "location": ".".join(str(part) for part in error["loc"]),
            "type": error["type"],
        }
        for error in exception.errors()
    ]
    return error_response(
        ApiException(
            status_code=422,
            code="INVALID_REQUEST",
            message="The request contains an invalid or unsupported value.",
            details={"fields": fields},
        )
    )


async def vlc_exception_handler(
    _request: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, VlcError):  # pragma: no cover - registration guard
        raise exception
    if isinstance(exception, VlcAuthenticationFailed):
        api_exception = ApiException(
            status_code=502,
            code="VLC_AUTHENTICATION_FAILED",
            message="VLC rejected the password stored by the remote service.",
            retryable=False,
        )
    elif isinstance(exception, VlcUnavailable):
        api_exception = ApiException(
            status_code=503,
            code="VLC_UNAVAILABLE",
            message="The remote service is running, but VLC could not be reached.",
            retryable=True,
        )
    elif isinstance(exception, VlcUnsupportedOperation):
        api_exception = ApiException(
            status_code=409,
            code="UNSUPPORTED_OPERATION",
            message="This operation is not supported by the installed VLC setup.",
            retryable=False,
        )
    else:
        api_exception = ApiException(
            status_code=502,
            code="VLC_COMMAND_FAILED",
            message="VLC could not complete the requested operation.",
            retryable=True,
        )
    return error_response(api_exception)


async def opensubtitles_exception_handler(
    _request: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, OpenSubtitlesError):  # pragma: no cover
        raise exception
    if isinstance(exception, OpenSubtitlesNotConfigured):
        api_exception = ApiException(
            status_code=409,
            code="OPENSUBTITLES_NOT_CONFIGURED",
            message="Online subtitles are not configured on this Mac.",
            retryable=False,
        )
    elif isinstance(exception, OpenSubtitlesAuthenticationFailed):
        api_exception = ApiException(
            status_code=502,
            code="OPENSUBTITLES_AUTHENTICATION_FAILED",
            message="OpenSubtitles rejected the account configured on this Mac.",
            retryable=False,
        )
    else:
        api_exception = ApiException(
            status_code=503,
            code="OPENSUBTITLES_UNAVAILABLE",
            message="OpenSubtitles could not be reached. Try again shortly.",
            retryable=True,
        )
    return error_response(api_exception)
