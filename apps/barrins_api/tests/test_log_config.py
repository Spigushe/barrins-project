"""Tests for app/core/log_config.py — coverage of the rotate() method."""

# pyright: reportPrivateUsage=none, reportUnknownMemberType=none, reportUnknownVariableType=none, reportUnknownArgumentType=none, reportUnknownParameterType=none, reportMissingParameterType=none

from app.core.log_config import _WindowsSafeRotatingFileHandler


class TestWindowsSafeRotatingFileHandler:
    def test_rotate_copies_source_to_dest_and_truncates(self, tmp_path):
        """rotate() copie source → dest et vide source."""
        source = tmp_path / "app.log"
        dest = tmp_path / "app.log.1"
        source.write_text("log content", encoding="utf-8")

        handler = _WindowsSafeRotatingFileHandler(
            filename=str(source), maxBytes=1024, backupCount=1
        )
        handler.rotate(str(source), str(dest))
        handler.close()

        assert dest.read_text(encoding="utf-8") == "log content"
        assert source.read_text(encoding="utf-8") == ""

    def test_rotate_overwrites_existing_dest(self, tmp_path):
        """rotate() supprime dest existant avant de copier."""
        source = tmp_path / "app.log"
        dest = tmp_path / "app.log.1"
        source.write_text("new content", encoding="utf-8")
        dest.write_text("old content", encoding="utf-8")

        handler = _WindowsSafeRotatingFileHandler(
            filename=str(source), maxBytes=1024, backupCount=1
        )
        handler.rotate(str(source), str(dest))
        handler.close()

        assert dest.read_text(encoding="utf-8") == "new content"
        assert source.read_text(encoding="utf-8") == ""
