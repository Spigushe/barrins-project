import pytest

from karn_tablets import config


class TestConfig:
    def test_database_url_reads_the_expected_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("KARN_TABLETS_DATABASE_URL_RO", "postgresql://ro@host/db")
        assert config.database_url() == "postgresql://ro@host/db"

    def test_database_url_none_when_unset(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("KARN_TABLETS_DATABASE_URL_RO", raising=False)
        assert config.database_url() is None

    def test_barrins_api_url_reads_the_expected_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("BARRINS_API_URL", "https://api.example.com")
        assert config.barrins_api_url() == "https://api.example.com"

    def test_karn_ingest_token_reads_the_expected_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("KARN_INGEST_TOKEN", "secret")
        assert config.karn_ingest_token() == "secret"
