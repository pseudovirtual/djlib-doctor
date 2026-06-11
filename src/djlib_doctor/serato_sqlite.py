from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any


SERATO_INSPECTION_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class SeratoTableInspection:
    name: str
    columns: tuple[str, ...]
    row_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "columns": list(self.columns),
            "row_count": self.row_count,
        }


@dataclass(frozen=True)
class SeratoInspection:
    root_sqlite: str
    tables: tuple[SeratoTableInspection, ...]
    schema_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SERATO_INSPECTION_SCHEMA_VERSION,
            "source": {
                "type": "serato_root_sqlite",
                "path": self.root_sqlite,
            },
            "summary": {
                "tables": len(self.tables),
                "total_rows": sum(table.row_count for table in self.tables),
            },
            "schema_fingerprint": self.schema_fingerprint,
            "tables": [table.to_dict() for table in self.tables],
        }

    def render_json(self, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(self.to_dict(), indent=2, sort_keys=True)
        return json.dumps(self.to_dict(), sort_keys=True)


def inspect_serato_root_sqlite(path: Path) -> SeratoInspection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        table_names = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        tables = []
        schema_parts = []
        for name in table_names:
            columns = tuple(row[1] for row in conn.execute(f"PRAGMA table_info({_quote_identifier(name)})"))
            row_count = int(conn.execute(f"SELECT COUNT(*) FROM {_quote_identifier(name)}").fetchone()[0])
            tables.append(SeratoTableInspection(name=name, columns=columns, row_count=row_count))
            schema_parts.append(f"{name}:{','.join(columns)}")
        fingerprint = hashlib.sha256("\n".join(schema_parts).encode("utf-8")).hexdigest()
        return SeratoInspection(root_sqlite=str(path), tables=tuple(tables), schema_fingerprint=fingerprint)
    finally:
        conn.close()


def write_serato_inspection(inspection: SeratoInspection, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "serato-inspection.json"
    path.write_text(inspection.render_json(pretty=True) + "\n", encoding="utf-8")
    return path


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'
