"""Tests for the local memory store."""

import json
import pytest
import tempfile

from src.memory.memory_store import MemoryStore


@pytest.fixture
def memory_store(tmp_path):
    """Create a memory store in a temp directory."""
    return MemoryStore(store_path=str(tmp_path / "test_store"))


class TestMemoryStore:
    def test_write_and_read(self, memory_store):
        memory_store.write("/drugs/nexavirin/notes", "Nexavirin shows good oral bioavailability")
        result = memory_store.read("/drugs/nexavirin/notes")
        assert result is not None
        assert "Nexavirin" in result["content"]

    def test_versioning(self, memory_store):
        memory_store.write("/test/item", "Version 1 content")
        memory_store.write("/test/item", "Version 2 content")
        result = memory_store.read("/test/item")
        assert result["version"] == 2
        assert "Version 2" in result["content"]

    def test_version_history(self, memory_store):
        memory_store.write("/test/versioned", "V1")
        memory_store.write("/test/versioned", "V2")
        memory_store.write("/test/versioned", "V3")
        versions = memory_store.get_versions("/test/versioned")
        assert len(versions) == 3

    def test_search(self, memory_store):
        memory_store.write("/drugs/nexavirin", "Antiviral compound targeting RdRp")
        memory_store.write("/drugs/oncolytin", "Kinase inhibitor for NSCLC")
        results = memory_store.search("antiviral")
        assert len(results) >= 1
        assert any("Antiviral" in r["content"] for r in results)

    def test_search_with_tags(self, memory_store):
        memory_store.write("/trial/pct001", "Phase II trial", tags=["clinical_trials"])
        memory_store.write("/drug/pha001", "Drug compound", tags=["drug_discovery"])
        results = memory_store.search("trial", tags=["clinical_trials"])
        # Should only return tagged results
        for r in results:
            assert "clinical_trials" in r["tags"]

    def test_delete(self, memory_store):
        memory_store.write("/temp/item", "Temporary data")
        assert memory_store.read("/temp/item") is not None
        memory_store.delete("/temp/item")
        assert memory_store.read("/temp/item") is None

    def test_delete_preserves_versions(self, memory_store):
        memory_store.write("/versioned/item", "Content v1")
        memory_store.write("/versioned/item", "Content v2")
        memory_store.delete("/versioned/item")
        versions = memory_store.get_versions("/versioned/item")
        assert len(versions) == 2  # Versions preserved

    def test_list_memories(self, memory_store):
        memory_store.write("/drugs/a", "Drug A")
        memory_store.write("/drugs/b", "Drug B")
        memory_store.write("/trials/c", "Trial C")
        results = memory_store.list_memories("/drugs/")
        assert len(results) == 2

    def test_content_size_limit(self, memory_store):
        with pytest.raises(ValueError, match="100KB"):
            memory_store.write("/huge", "x" * (101 * 1024))

    def test_read_nonexistent(self, memory_store):
        assert memory_store.read("/nonexistent") is None

    def test_agent_context(self, memory_store):
        memory_store.write("/context/drug_discovery", "Important drug context", tags=["drug_discovery"])
        context = memory_store.get_context_for_agent("drug_discovery")
        assert "drug_discovery" in context
        assert "Important drug context" in context
