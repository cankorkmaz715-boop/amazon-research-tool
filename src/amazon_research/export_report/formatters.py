"""
Step 228: Export formatters – CSV and safe serialization for list-like data.
No sensitive or internal debug data. Workspace-scoped exports only.
"""
from typing import Any, Dict, List


def _csv_escape(val: Any) -> str:
    """Escape a value for CSV (quote if contains comma, newline, or quote)."""
    if val is None:
        return ""
    s = str(val).strip()
    if "," in s or "\n" in s or '"' in s:
        s = '"' + s.replace('"', '""') + '"'
    return s


def rows_to_csv(rows: List[Dict[str, Any]], columns: List[str]) -> str:
    """
    Convert a list of dicts to CSV. Uses columns as header and key order.
    Missing keys become empty cells. No secrets or internal fields.
    """
    if not columns:
        return ""
    lines = [",".join(_csv_escape(c) for c in columns)]
    for row in rows:
        if not isinstance(row, dict):
            continue
        cells = [_csv_escape(row.get(c)) for c in columns]
        lines.append(",".join(cells))
    return "\n".join(lines)
