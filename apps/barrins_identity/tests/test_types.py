"""Tests for app/models/_types.py — JSONBCompat dialect branches."""

from unittest.mock import MagicMock

import pytest

from app.models._types import JSONBCompat, jsonb_column


class TestJSONBCompat:
    def test_load_dialect_impl_postgresql(self):
        dialect = MagicMock()
        dialect.name = "postgresql"
        impl = JSONBCompat().load_dialect_impl(dialect)
        assert impl is not None

    def test_load_dialect_impl_other_dialect(self):
        dialect = MagicMock()
        dialect.name = "sqlite"
        impl = JSONBCompat().load_dialect_impl(dialect)
        assert impl is not None

    def test_process_bind_param_none(self):
        assert JSONBCompat().process_bind_param(None, MagicMock()) is None

    def test_process_bind_param_valid(self):
        value = {"a": [1, 2, "x"]}
        assert JSONBCompat().process_bind_param(value, MagicMock()) == value

    def test_process_bind_param_rejects_non_serializable(self):
        with pytest.raises(ValueError, match="not JSON-serializable"):
            JSONBCompat().process_bind_param(object(), MagicMock())  # type: ignore[arg-type]

    def test_process_result_value(self):
        assert JSONBCompat().process_result_value(None, MagicMock()) is None
        assert JSONBCompat().process_result_value({"a": 1}, MagicMock()) == {"a": 1}


class TestJsonbColumn:
    def test_default_nullable_false(self):
        col = jsonb_column(default=[], nullable=False)
        assert col is not None

    def test_no_default_nullable_true(self):
        col = jsonb_column(nullable=True)
        assert col is not None
