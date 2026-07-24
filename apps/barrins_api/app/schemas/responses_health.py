"""Response schema for the health check endpoint."""

from typing import Literal

from app.schemas.responses_base import BaseResponse


class HealthResponse(BaseResponse):
    status: Literal["ok"]
