"""Tests for error handlers, custom exceptions, and auth stub.

Covers:
- app/core/exceptions.py  (AppException hierarchy)
- app/core/error_handlers.py (app/validation/pydantic/generic handlers)
- app/dependencies/auth.py  (get_current_user stub → 501)
- app/dependencies/__init__.py (DatabaseSession re-export)
"""

# pyright: reportUnknownMemberType=none, reportUnknownVariableType=none, reportUnknownArgumentType=none, reportUnknownParameterType=none, reportMissingParameterType=none, reportUnusedFunction=none

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.error_handlers import register_exception_handlers
from app.core.exceptions import (
    AppException,
    BadRequestError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
)
from app.core.exceptions import ValidationError as AppValidationError


# ---------------------------------------------------------------------------
# AppException hierarchy — no DB, no HTTP
# ---------------------------------------------------------------------------
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
        assert exc.error_code == "RESOURCE_NOT_FOUND"

    def test_already_exists(self):
        exc = ResourceAlreadyExistsError()
        assert exc.status_code == 409
        assert exc.error_code == "RESOURCE_ALREADY_EXISTS"

    def test_app_validation_error(self):
        exc = AppValidationError()
        assert exc.status_code == 400
        assert exc.error_code == "VALIDATION_ERROR"

    def test_bad_request(self):
        exc = BadRequestError()
        assert exc.status_code == 400
        assert exc.error_code == "BAD_REQUEST"


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------
async def test_auth_dependency_requires_bearer(client: AsyncClient):
    """get_current_user without a Bearer token returns HTTP 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Mini FastAPI app for handler integration tests
# ---------------------------------------------------------------------------
class _Item(BaseModel):
    value: int


@pytest.fixture(scope="module")
def handler_app() -> FastAPI:
    """Minimal application with all handlers registered."""
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
        transport=ASGITransport(app=handler_app),
        base_url="http://test",
    ) as ac:
        yield ac


class TestErrorHandlers:
    async def test_app_exception_handler(self, handler_client: AsyncClient):
        """AppException → JSONResponse with the correct error format."""
        response = await handler_client.get("/app-exc")
        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert body["error"]["message"] == "test app exc"
        assert body["error"]["details"] == {"k": "v"}
        assert "request_id" in body["error"]
        assert "timestamp" in body["error"]

    async def test_validation_exception_handler(self, handler_client: AsyncClient):
        """RequestValidationError → 422 with a list of errors."""
        response = await handler_client.get("/validation/not-a-number")
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "validation_errors" in body["error"]["details"]
        assert len(body["error"]["details"]["validation_errors"]) > 0

    async def test_pydantic_exception_handler(self, handler_client: AsyncClient):
        """Manually raised PydanticValidationError → 422."""
        response = await handler_client.get("/pydantic-exc")
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "validation_errors" in body["error"]["details"]

    async def test_generic_exception_handler(self):
        """generic_exception_handler → 500 INTERNAL_SERVER_ERROR.

        Tested directly (bypassing middleware) because ServerErrorMiddleware
        intercepts raw exceptions before the registered handlers.
        """
        from unittest.mock import MagicMock

        from app.core.error_handlers import generic_exception_handler

        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.url.path = "/test-path"

        response = await generic_exception_handler(request, ValueError("oops"))
        assert response.status_code == 500
        import json

        body = json.loads(response.body)
        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert body["error"]["message"] == "An unexpected error occurred"
