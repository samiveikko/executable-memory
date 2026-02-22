"""Run ID generation."""

from __future__ import annotations

import uuid


def generate_run_id() -> str:
    """Generate a unique run ID."""
    return str(uuid.uuid4())
