"""UDFs for csv_report routine — deterministic data processing functions."""

from __future__ import annotations

import csv
import io
from typing import Any


def parse_and_clean(raw_csv: str) -> list[dict[str, Any]]:
    """Parse CSV text and clean/normalize the data."""
    reader = csv.DictReader(io.StringIO(raw_csv.strip()))
    rows = []
    for row in reader:
        cleaned = {}
        for key, value in row.items():
            key = key.strip().lower()
            value = value.strip()
            # Try numeric conversion
            try:
                if "." in value:
                    cleaned[key] = float(value)
                else:
                    cleaned[key] = int(value)
            except ValueError:
                cleaned[key] = value
        rows.append(cleaned)
    return rows


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize parsed rows into a report."""
    if not rows:
        return {"total_rows": 0, "departments": {}, "total_cost": 0}

    departments: dict[str, list[dict]] = {}
    for row in rows:
        dept = row.get("department", "unknown")
        departments.setdefault(dept, []).append(row)

    dept_summaries = {}
    total_cost = 0.0
    for dept, members in departments.items():
        dept_hours = sum(m.get("hours", 0) for m in members)
        dept_cost = sum(m.get("hours", 0) * m.get("rate", 0) for m in members)
        total_cost += dept_cost
        dept_summaries[dept] = {
            "headcount": len(members),
            "total_hours": dept_hours,
            "total_cost": dept_cost,
        }

    return {
        "total_rows": len(rows),
        "departments": dept_summaries,
        "total_cost": total_cost,
    }


def is_ambiguous_delimiter(raw_csv: str) -> bool:
    """Check if the CSV might have an ambiguous delimiter."""
    first_line = raw_csv.strip().split("\n")[0]
    comma_count = first_line.count(",")
    tab_count = first_line.count("\t")
    semicolon_count = first_line.count(";")
    counts = sorted([comma_count, tab_count, semicolon_count], reverse=True)
    # Ambiguous if top two delimiters have similar counts
    return counts[0] > 0 and counts[1] > 0 and counts[0] - counts[1] <= 1


def guess_delimiter(raw_csv: str) -> str:
    """Guess the most likely delimiter."""
    first_line = raw_csv.strip().split("\n")[0]
    for delim in [",", "\t", ";", "|"]:
        if delim in first_line:
            return delim
    return ","


def count(rows: list) -> int:
    """Return the number of rows."""
    return len(rows)
