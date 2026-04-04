from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.state import Reflection


class ReflectionStore:
    """
    Persistent store for reflections across runs.

    Phase 1: Flat JSON files per (run_id, task_id). No retrieval.
    Phase 2: Vector store (FAISS / Chroma) for cross-run similarity search.

    The interface is already designed for Phase 2 — query() accepts a
    text query — so swapping the backend only requires changing this file.

    Storage layout:
        memory/
            {run_id}_{task_id}.json    <- list of Reflection dicts
    """

    def __init__(self, store_dir: Path = Path("memory")) -> None:
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def save(self, run_id: str, task_id: str, reflections: list[Reflection]) -> None:
        """Persist all reflections from a run to disk."""
        path = self.store_dir / f"{run_id}_{task_id}.json"
        data = [r.model_dump() for r in reflections]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, run_id: str, task_id: str) -> list[Reflection]:
        """Load reflections for a specific run."""
        path = self.store_dir / f"{run_id}_{task_id}.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [Reflection(**r) for r in data]

    def query(self, text: str, task_id: str | None = None, top_k: int = 3) -> list[Reflection]:
        """
        Retrieve relevant reflections by similarity to `text`.

        Phase 1: Returns the most recent reflections (recency heuristic).
        Phase 2: Replace with vector similarity search.
        """
        all_reflections: list[Reflection] = []
        for path in sorted(self.store_dir.glob("*.json"), reverse=True):
            if task_id and task_id not in path.stem:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                all_reflections.extend(Reflection(**r) for r in data)
            except Exception:
                continue

        # Phase 1 fallback: most recent top_k
        return all_reflections[:top_k]
