"""Tests for EpicStorage."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jitsu.core.storage import EpicStorage


@pytest.fixture
def storage(tmp_path: Path) -> EpicStorage:
    """Return a storage instance rooted at tmp_path."""
    return EpicStorage(base_dir=tmp_path)


class TestEpicStorageDirectories:
    """Tests for directory properties."""

    def test_current_dir_created(self, storage: EpicStorage, tmp_path: Path) -> None:
        """current_dir creates and returns the correct path."""
        d = storage.current_dir
        assert d == tmp_path / ".jitsu" / "epics"
        assert d.exists()

    def test_completed_dir_created(self, storage: EpicStorage, tmp_path: Path) -> None:
        """completed_dir creates and returns the correct path."""
        d = storage.completed_dir
        assert d == tmp_path / ".jitsu" / "completed"
        assert d.exists()

    def test_default_base_dir(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """EpicStorage defaults to Path.home() when base_dir is not given."""

        def mock_home() -> Path:
            return tmp_path

        monkeypatch.setattr(Path, "home", mock_home)
        s = EpicStorage()
        assert s.base_dir == tmp_path

    def test_get_current_path(self, storage: EpicStorage, tmp_path: Path) -> None:
        """get_current_path returns the correct path for an epic_id."""
        p = storage.get_current_path("epic-123")
        assert p == tmp_path / ".jitsu" / "epics" / "epic-123.json"


class TestEpicStorageReadText:
    """Tests for read_text."""

    def test_read_text_success(self, storage: EpicStorage, tmp_path: Path) -> None:
        """read_text returns file content as string."""
        f = tmp_path / "epic.json"
        f.write_text("hello", encoding="utf-8")
        assert storage.read_text(f) == "hello"

    def test_read_text_os_error(self, storage: EpicStorage, tmp_path: Path) -> None:
        """read_text propagates OSError when file is missing."""
        missing = tmp_path / "no_file.json"
        with pytest.raises(OSError, match="No such file or directory"):
            storage.read_text(missing)


class TestEpicStorageReadBytes:
    """Tests for read_bytes."""

    def test_read_bytes_success(self, storage: EpicStorage, tmp_path: Path) -> None:
        """read_bytes returns file content as bytes."""
        f = tmp_path / "epic.json"
        f.write_bytes(b"bytes")
        assert storage.read_bytes(f) == b"bytes"

    def test_read_bytes_os_error(self, storage: EpicStorage, tmp_path: Path) -> None:
        """read_bytes propagates OSError when file is missing."""
        missing = tmp_path / "no_file.json"
        with pytest.raises(OSError, match="No such file or directory"):
            storage.read_bytes(missing)


class TestEpicStorageArchive:
    """Tests for archive."""

    def test_archive_moves_file(self, storage: EpicStorage, tmp_path: Path) -> None:
        """Archive renames the source file to the completed directory."""
        src = tmp_path / "epic.json"
        src.write_text("[]", encoding="utf-8")

        dest = storage.archive(src)

        assert dest == tmp_path / ".jitsu" / "completed" / "epic.json"
        assert dest.exists()
        assert not src.exists()

    def test_archive_returns_dest_path(self, storage: EpicStorage, tmp_path: Path) -> None:
        """Archive returns the destination path."""
        src = tmp_path / "myepic.json"
        src.write_text("[]", encoding="utf-8")

        dest = storage.archive(src)
        assert dest.name == "myepic.json"

    def test_archive_os_error(self, storage: EpicStorage, tmp_path: Path) -> None:
        """Archive propagates OSError if rename fails."""
        src = tmp_path / "epic.json"
        src.write_text("[]", encoding="utf-8")

        with (
            patch.object(Path, "rename", side_effect=OSError("rename failed")),
            pytest.raises(OSError, match="rename failed"),
        ):
            storage.archive(src)


class TestEpicStorageCompletedRel:
    """Tests for completed_rel."""

    def test_completed_rel_returns_relative_path(
        self, storage: EpicStorage, tmp_path: Path
    ) -> None:
        """completed_rel returns path relative to the base dir."""
        dest = tmp_path / ".jitsu" / "completed" / "epic.json"
        rel = storage.completed_rel(dest)
        assert rel == ".jitsu/completed/epic.json"
