"""Strict request models for the fixed set of browser-exposed commands."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt


class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RelativeSeekRequest(CommandModel):
    mode: Literal["relative"]
    seconds: Annotated[StrictInt, Field(ge=-3600, le=3600)]


class AbsoluteSeekRequest(CommandModel):
    mode: Literal["absolute"]
    seconds: Annotated[StrictInt, Field(ge=0)]


SeekRequest = Annotated[
    RelativeSeekRequest | AbsoluteSeekRequest,
    Field(discriminator="mode"),
]


class VolumeRequest(CommandModel):
    percent: Annotated[StrictInt, Field(ge=0, le=100)]


class MuteRequest(CommandModel):
    muted: StrictBool


class RateRequest(CommandModel):
    rate: Annotated[
        StrictFloat,
        Field(ge=0.25, le=4.0, allow_inf_nan=False),
    ]
