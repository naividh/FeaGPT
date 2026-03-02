"""
File I/O and workspace management for FeaGPT.
"""
import json
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages workspace directories for FEA jobs."""

    SUBDIRS = ["input", "output", "mesh", "geometry", "reports"]

    def __init__(self, base_path: str):
        self.base = Path(base_path)

    def setup(self):
        """Create workspace directory structure."""
        self.base.mkdir(parents=True, exist_ok=True)
        for sub in self.SUBDIRS:
            (self.base / sub).mkdir(exist_ok=True)
        logger.info(f"Workspace ready: {self.base}")

    def write_file(self, rel_path: str, content: str):
        """Write content to a file in the workspace."""
        full_path = self.base / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    def read_file(self, rel_path: str) -> str:
        """Read content from a workspace file."""
        full_path = self.base / rel_path
        return full_path.read_text()

    def write_json(self, rel_path: str, data: Any):
        """Write JSON data to a workspace file."""
        full_path = self.base / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def read_json(self, rel_path: str) -> Any:
        """Read JSON data from a workspace file."""
        full_path = self.base / rel_path
        with open(full_path, "r") as f:
            return json.load(f)

    def exists(self, rel_path: str) -> bool:
        """Check if a file exists in the workspace."""
        return (self.base / rel_path).exists()

    def list_files(
        self, subdir: str = "", pattern: str = "*"
    ):
        """List files in a workspace subdirectory."""
        search_dir = self.base / subdir
        if search_dir.exists():
            return list(search_dir.glob(pattern))
        return []

    def clean(self, subdir: Optional[str] = None):
        """Clean workspace or specific subdirectory."""
        target = self.base / subdir if subdir else self.base
        if target.exists():
            shutil.rmtree(target)
            if subdir:
                target.mkdir(exist_ok=True)
            logger.info(f"Cleaned: {target}")

    def get_path(self, rel_path: str) -> Path:
        """Get absolute path for a relative workspace path."""
        return self.base / rel_path
