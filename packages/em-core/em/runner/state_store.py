"""State store — save/restore execution state for pause/resume."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class RunState:
    """Snapshot of a paused routine execution."""

    def __init__(
        self,
        run_id: str,
        routine_dir: str,
        step_index: int,
        context: dict[str, Any],
        pending_step_id: str,
    ):
        self.run_id = run_id
        self.routine_dir = routine_dir
        self.step_index = step_index
        self.context = context
        self.pending_step_id = pending_step_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "routine_dir": self.routine_dir,
            "step_index": self.step_index,
            "context": self.context,
            "pending_step_id": self.pending_step_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunState:
        return cls(**data)


class StateStore(Protocol):
    """Protocol for state persistence."""

    def save(self, state: RunState) -> None: ...
    def load(self, run_id: str) -> RunState | None: ...
    def delete(self, run_id: str) -> None: ...


class InMemoryStateStore:
    """In-memory state store — lost on process exit."""

    def __init__(self) -> None:
        self._states: dict[str, RunState] = {}

    def save(self, state: RunState) -> None:
        self._states[state.run_id] = state

    def load(self, run_id: str) -> RunState | None:
        return self._states.get(run_id)

    def delete(self, run_id: str) -> None:
        self._states.pop(run_id, None)


class FileStateStore:
    """File-backed state store for durable pause/resume."""

    def __init__(self, state_dir: Path):
        self._dir = state_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self._dir / f"{run_id}.json"

    def save(self, state: RunState) -> None:
        with open(self._path(state.run_id), "w") as f:
            json.dump(state.to_dict(), f)

    def load(self, run_id: str) -> RunState | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        with open(path) as f:
            return RunState.from_dict(json.load(f))

    def delete(self, run_id: str) -> None:
        path = self._path(run_id)
        if path.exists():
            path.unlink()
