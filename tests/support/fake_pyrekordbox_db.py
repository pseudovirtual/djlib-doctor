from __future__ import annotations


class FakePyrekordboxDb:
    def __init__(self) -> None:
        self.engine = _FakeEngine(self)
        self.statements: list[str] = []
        self.closed = False
        self.disposed = False

    def close(self) -> None:
        self.closed = True


class _FakeEngine:
    def __init__(self, db: FakePyrekordboxDb) -> None:
        self.db = db

    def begin(self) -> _FakeConnection:
        return _FakeConnection(self.db)

    def connect(self) -> _FakeConnection:
        return _FakeConnection(self.db)

    def dispose(self) -> None:
        self.db.disposed = True


class _FakeConnection:
    def __init__(self, db: FakePyrekordboxDb) -> None:
        self.db = db

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def execute(self, statement: object, _params: object | None = None) -> _FakeRows:
        sql = str(statement)
        self.db.statements.append(sql)
        if "PRAGMA integrity_check" in sql:
            return _FakeRows([("ok",)])
        if "PRAGMA wal_checkpoint" in sql:
            return _FakeRows([(0, 0, 0)])
        return _FakeRows([])

    def execution_options(self, **_options: object) -> _FakeConnection:
        return self


class _FakeRows(list):
    def fetchall(self) -> _FakeRows:
        return self
