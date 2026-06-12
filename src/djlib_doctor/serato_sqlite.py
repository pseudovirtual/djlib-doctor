from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import sqlite3
from typing import Any

from .io_utils import render_json, write_json
from .sqlite_utils import quote_identifier


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
    asset_identity: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
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
        if self.asset_identity is not None:
            data["asset_identity"] = self.asset_identity
        return data

    def render_json(self, pretty: bool = False) -> str:
        return render_json(self.to_dict(), pretty=pretty)


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
            columns = tuple(row[1] for row in conn.execute(f"PRAGMA table_info({quote_identifier(name)})"))
            row_count = int(conn.execute(f"SELECT COUNT(*) FROM {quote_identifier(name)}").fetchone()[0])
            tables.append(SeratoTableInspection(name=name, columns=columns, row_count=row_count))
            schema_parts.append(f"{name}:{','.join(columns)}")
        fingerprint = hashlib.sha256("\n".join(schema_parts).encode("utf-8")).hexdigest()
        asset_identity = _inspect_asset_identity(conn, tuple(tables))
        return SeratoInspection(
            root_sqlite=str(path),
            tables=tuple(tables),
            schema_fingerprint=fingerprint,
            asset_identity=asset_identity,
        )
    finally:
        conn.close()


def write_serato_inspection(inspection: SeratoInspection, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "serato-inspection.json"
    write_json(path, inspection.to_dict())
    return path


def _inspect_asset_identity(
    conn: sqlite3.Connection,
    tables: tuple[SeratoTableInspection, ...],
) -> dict[str, Any] | None:
    asset_table = next((table for table in tables if table.name == "asset"), None)
    if asset_table is None or "portable_id" not in asset_table.columns:
        return None
    asset_name = quote_identifier(asset_table.name)
    portable_id = quote_identifier("portable_id")
    total_assets = int(conn.execute(f"SELECT COUNT(*) FROM {asset_name}").fetchone()[0])
    assets_with_identity = int(
        conn.execute(
            f"SELECT COUNT(*) FROM {asset_name} WHERE {portable_id} IS NOT NULL AND TRIM({portable_id}) != ''"
        ).fetchone()[0]
    )
    duplicate_identity_values = int(
        conn.execute(
            f"""
            SELECT COUNT(*) FROM (
                SELECT {portable_id}
                FROM {asset_name}
                WHERE {portable_id} IS NOT NULL AND TRIM({portable_id}) != ''
                GROUP BY {portable_id}
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
    )
    return {
        "identity_field": "asset.portable_id",
        "identity_meaning": "Serato local asset identity is commonly path-like portable_id data.",
        "total_assets": total_assets,
        "assets_with_identity": assets_with_identity,
        "duplicate_identity_values": duplicate_identity_values,
    }
