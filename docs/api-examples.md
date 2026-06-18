# Python API Examples

`djlib-doctor` is primarily a CLI, but its modules can also be used as small building blocks in other tools. Prefer read-only functions first and keep staged write workflows behind their CLI or manifest APIs.

## Verify A Rekordbox XML Export

```python
from pathlib import Path

from djlib_doctor.rekordbox_xml import parse_rekordbox_xml
from djlib_doctor.verify import verify_library

library = parse_rekordbox_xml(Path("rekordbox-export.xml"))
report = verify_library(library, check_files=False)
print(report.status)
```

## Build A Missing-File Plan

```python
from pathlib import Path

from djlib_doctor.plan import build_missing_files_plan, write_plan
from djlib_doctor.snapshot import create_snapshot

snapshot = create_snapshot(Path("rekordbox-export.xml"), music_root=Path("~/Music").expanduser())
plan = build_missing_files_plan(snapshot)
write_plan(plan, Path("run/missing-files.json"))
```

## Compare Two Exports

```python
from pathlib import Path

from djlib_doctor.compare import compare_exports

report = compare_exports(Path("before.xml"), Path("after.xml"), check_files=False)
print(report.summary)
```

For write workflows, prefer the staged CLI commands so token checks, hashes, backups, sidecar checks, and app-closed checks stay intact.
