"""EpicStorage: Encapsulates all file I/O for epic tracking and archiving."""

from pathlib import Path


class EpicStorage:
    """
    Encapsulates disk I/O operations for Jitsu epic files.

    Manages loading epic JSON, writing bytes, and archiving completed epics
    to the ``epics/completed/`` directory.

    Args:
        base_dir: The project root directory.  Defaults to ``Path.cwd()``.

    """

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialise storage with an optional base directory."""
        self.base_dir = base_dir or Path.cwd()

    # ------------------------------------------------------------------
    # Directory helpers
    # ------------------------------------------------------------------

    @property
    def current_dir(self) -> Path:
        """Return the epics/current directory, creating it if necessary."""
        p = self.base_dir / "epics" / "current"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_current_path(self, epic_id: str) -> Path:
        """Return the path for a given epic_id in the current directory."""
        return self.current_dir / f"{epic_id}.json"

    @property
    def completed_dir(self) -> Path:
        """Return the epics/completed directory, creating it if necessary."""
        p = self.base_dir / "epics" / "completed"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def read_text(self, path: Path) -> str:
        """
        Read and return the text content of an epic JSON file.

        Args:
            path: Path to the JSON file.

        Returns:
            The file content as a string.

        Raises:
            OSError: If the file cannot be read.

        """
        return path.read_text(encoding="utf-8")

    def read_bytes(self, path: Path) -> bytes:
        """
        Read and return the raw bytes of an epic JSON file.

        Args:
            path: Path to the JSON file.

        Returns:
            The file content as bytes.

        Raises:
            OSError: If the file cannot be read.

        """
        return path.read_bytes()

    # ------------------------------------------------------------------
    # Write / archive helpers
    # ------------------------------------------------------------------

    def archive(self, path: Path) -> Path:
        """
        Move an epic file to the completed directory.

        Args:
            path: Source path of the epic JSON file.

        Returns:
            The new path inside ``epics/completed/``.

        Raises:
            OSError: If the rename operation fails.

        """
        dest = self.completed_dir / path.name
        path.rename(dest)
        return dest

    def rel_path(self, path: Path) -> str:
        """
        Return the path relative to the base directory.

        Args:
            path: Absolute path to relativize.

        Returns:
            A human-readable relative path string.

        """
        return str(path.relative_to(self.base_dir))

    def completed_rel(self, dest: Path) -> str:
        """
        Return the completed path relative to the base directory.

        Args:
            dest: Absolute path inside the completed directory.

        Returns:
            A human-readable relative path string.

        """
        return self.rel_path(dest)
