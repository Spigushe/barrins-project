"""Tests for app/core/exceptions.py and app/core/error_handlers.py."""

import json
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.error_handlers import (
    generic_exception_handler,
    register_exception_handlers,
)
from app.core.exceptions import (
    AppException,
    BadRequestError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
)
from app.core.exceptions import ValidationError as AppValidationError


class TestAppException:
    def test_default_values(self):
        exc = AppException()
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.status_code == 500
        assert exc.details == {}

    def test_custom_message(self):
        exc = AppException(message="custom msg")
        assert exc.message == "custom msg"
        assert str(exc) == "custom msg"

    def test_custom_error_code(self):
        exc = AppException(error_code="MY_CODE")
        assert exc.error_code == "MY_CODE"

    def test_details(self):
        exc = AppException(details={"key": "value"})
        assert exc.details == {"key": "value"}

    def test_resource_not_found(self):
        exc = ResourceNotFoundError()
        assert exc.status_code == 404

    def test_already_exists(self):
        exc = ResourceAlreadyExistsError()
        assert exc.status_code == 409

    def test_app_validation_error(self):
        exc = AppValidationError()
        assert exc.status_code == 400

    def test_bad_request(self):
        exc = BadRequestError()
        assert exc.status_code == 400


class _Item(BaseModel):
    value: int


@pytest.fixture(scope="module")
def handler_app() -> FastAPI:
    _app = FastAPI()
    register_exception_handlers(_app)

    @_app.get("/app-exc")
    async def raise_app_exc():
        raise AppException(message="test app exc", details={"k": "v"})

    @_app.get("/validation/{item_id}")
    async def typed_param(item_id: int):
        return {"id": item_id}

    @_app.get("/pydantic-exc")
    async def raise_pydantic():
        _Item.model_validate({"value": "not-an-int"})
        return {}

    return _app


@pytest.fixture()
async def handler_client(handler_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=handler_app), base_url="http://test"
    ) as ac:
        yield ac


class TestErrorHandlers:
    async def test_app_exception_handler(self, handler_client: AsyncClient):
        response = await handler_client.get("/app-exc")
        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert body["error"]["message"] == "test app exc"
        assert body["error"]["details"] == {"k": "v"}
        assert "request_id" in body["error"]
        assert "timestamp" in body["error"]

    async def test_validation_exception_handler(self, handler_client: AsyncClient):
        response = await handler_client.get("/validation/not-a-number")
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert len(body["error"]["details"]["validation_errors"]) > 0

    async def test_pydantic_exception_handler(self, handler_client: AsyncClient):
        response = await handler_client.get("/pydantic-exc")
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    async def test_generic_exception_handler(self):
        """Tested directly — Starlette's ServerErrorMiddleware intercepts
        raw exceptions before the registered handlers run in a real app."""
        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.url.path = "/test-path"

        response = await generic_exception_handler(request, ValueError("oops"))
        assert response.status_code == 500
        body = json.loads(response.body)
        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"

    async def test_rate_limit_exception_handler(self, client: AsyncClient):
        """Exercised end-to-end via the real 429 path — see test_rate_limit.py."""
        payload = {"username": "nobody@example.com", "password": "Whatever#1pass"}
        from app.config import settings

        for _ in range(int(settings.base.login_rate_limit.split("/")[0]) + 1):
            resp = await client.post("/api/v1/auth/token", data=payload)
        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
