"""Local file-based memory store with versioning and search.

Mirrors the Claude Managed Agents memory API locally for offline-first operation.
Supports read, write, edit, search, delete, and version history.
"""

from __future__ import annotations

import json
import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("memory")


class MemoryStore:
    """Persistent, file-based memory store with versioning and full-text search.

    Structure:
        store_root/
            index.json          — master index of all memories
            memories/
                <id>.json       — current memory content
            versions/
                <id>/
                    v1.json     — immutable version snapshots
                    v2.json
    """

    def __init__(self, store_path: str = "src/memory/store"):
        self._root = Path(__file__).parent.parent.parent / store_path
        self._memories_dir = self._root / "memories"
        self._versions_dir = self._root / "versions"
        self._index_path = self._root / "index.json"
        self._lock = threading.Lock()

        # Create directories
        self._memories_dir.mkdir(parents=True, exist_ok=True)
        self._versions_dir.mkdir(parents=True, exist_ok=True)

        # Load or create index
        if self._index_path.exists():
            with open(self._index_path, "r", encoding="utf-8") as f:
                self._index: dict[str, Any] = json.load(f)
        else:
            self._index = {"memories": {}, "created": datetime.now(timezone.utc).isoformat()}
            self._save_index()

        logger.info("Memory store initialized at %s (%d memories)", self._root, len(self._index["memories"]))

    def write(self, path: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
        """Create or overwrite a memory at the given path.

        Args:
            path: Logical path, e.g. "/drugs/nexavirin/interactions"
            content: Memory content (free-form text, up to 100KB).
            tags: Optional tags for categorization.

        Returns:
            The memory record with ID and version info.
        """
        if len(content.encode("utf-8")) > 100 * 1024:
            raise ValueError("Memory content exceeds 100KB limit")

        memory_id = self._path_to_id(path)
        now = datetime.now(timezone.utc).isoformat()
        is_update = memory_id in self._index["memories"]

        # Determine version
        version = 1
        if is_update:
            version = self._index["memories"][memory_id].get("version", 0) + 1

        memory_record = {
            "id": memory_id,
            "path": path,
            "content": content,
            "tags": tags or [],
            "version": version,
            "created_at": self._index["memories"].get(memory_id, {}).get("created_at", now),
            "updated_at": now,
        }

        with self._lock:
            # Write current state
            memory_file = self._memories_dir / f"{memory_id}.json"
            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(memory_record, f, indent=2)

            # Write version snapshot (immutable)
            version_dir = self._versions_dir / memory_id
            version_dir.mkdir(exist_ok=True)
            version_file = version_dir / f"v{version}.json"
            with open(version_file, "w", encoding="utf-8") as f:
                json.dump({**memory_record, "snapshot_at": now}, f, indent=2)

            # Update index
            self._index["memories"][memory_id] = {
                "path": path,
                "tags": tags or [],
                "version": version,
                "created_at": memory_record["created_at"],
                "updated_at": now,
                "content_preview": content[:100],
            }
            self._save_index()

        action = "updated" if is_update else "created"
        logger.info("Memory %s: %s (v%d)", action, path, version)
        return memory_record

    def read(self, path: str) -> dict[str, Any] | None:
        """Read a memory by its path."""
        memory_id = self._path_to_id(path)
        memory_file = self._memories_dir / f"{memory_id}.json"
        if not memory_file.exists():
            return None
        with open(memory_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def search(self, query: str, tags: list[str] | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Full-text search across all memories.

        Args:
            query: Search string (case-insensitive substring match).
            tags: Optional tag filter (memories must have all specified tags).
            limit: Maximum results to return.
        """
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        for memory_id, meta in self._index["memories"].items():
            # Tag filter
            if tags and not all(t in meta.get("tags", []) for t in tags):
                continue

            # Check path and preview
            if query_lower in meta["path"].lower() or query_lower in meta.get("content_preview", "").lower():
                memory = self.read(meta["path"])
                if memory:
                    results.append(memory)
                    if len(results) >= limit:
                        break
                continue

            # Check full content
            memory_file = self._memories_dir / f"{memory_id}.json"
            if memory_file.exists():
                with open(memory_file, "r", encoding="utf-8") as f:
                    memory = json.load(f)
                if query_lower in memory.get("content", "").lower():
                    results.append(memory)
                    if len(results) >= limit:
                        break

        return results

    def list_memories(self, path_prefix: str = "/", limit: int = 50) -> list[dict[str, Any]]:
        """List memories under a path prefix."""
        results: list[dict[str, Any]] = []
        for meta in self._index["memories"].values():
            if meta["path"].startswith(path_prefix):
                results.append(meta)
                if len(results) >= limit:
                    break
        return sorted(results, key=lambda x: x.get("updated_at", ""), reverse=True)

    def delete(self, path: str) -> bool:
        """Delete a memory (versions are preserved for audit trail)."""
        memory_id = self._path_to_id(path)
        if memory_id not in self._index["memories"]:
            return False

        with self._lock:
            memory_file = self._memories_dir / f"{memory_id}.json"
            if memory_file.exists():
                memory_file.unlink()
            del self._index["memories"][memory_id]
            self._save_index()

        logger.info("Memory deleted: %s (versions preserved)", path)
        return True

    def get_versions(self, path: str) -> list[dict[str, Any]]:
        """Get all version snapshots for a memory."""
        memory_id = self._path_to_id(path)
        version_dir = self._versions_dir / memory_id
        if not version_dir.exists():
            return []

        versions: list[dict[str, Any]] = []
        for version_file in sorted(version_dir.glob("v*.json")):
            with open(version_file, "r", encoding="utf-8") as f:
                versions.append(json.load(f))
        return versions

    def get_context_for_agent(self, agent_name: str) -> str:
        """Build a context string from relevant memories for a specific agent.

        Searches for memories tagged with the agent name and returns
        formatted context suitable for injection into the system prompt.
        """
        memories = self.search(agent_name, limit=20)
        agent_memories = [m for m in memories if agent_name in m.get("tags", [])]

        if not agent_memories:
            return ""

        lines = [f"## Recalled Memories for {agent_name}\n"]
        for mem in agent_memories:
            lines.append(f"### {mem['path']}")
            lines.append(mem["content"])
            lines.append("")

        return "\n".join(lines)

    def _path_to_id(self, path: str) -> str:
        """Convert a logical path to a stable filesystem-safe ID."""
        return hashlib.sha256(path.encode()).hexdigest()[:16]

    def _save_index(self) -> None:
        """Persist the index to disk."""
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2)
