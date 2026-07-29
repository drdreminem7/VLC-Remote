"""Movie artwork responses returned by the authenticated local API."""

from pydantic import BaseModel, ConfigDict

from backend.app.models.playback import to_camel


class ArtworkResponse(BaseModel):
    """An optional poster encoded for same-origin display on the phone."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
    )

    image_data: str | None = None
