from __future__ import annotations

import contextlib
import shutil
import sqlite3
import unittest
from pathlib import Path

from tests.support.rekordbox_encrypted_fixture import rekordbox_public_sqlcipher_key

from djlib_doctor.rekordbox_db_read import read_rekordbox_master_db
from djlib_doctor.rekordbox_xml import RekordboxLibrary


def assert_plain_sqlite_rejects(testcase: unittest.TestCase, db: Path) -> None:
    with testcase.assertRaisesRegex(sqlite3.DatabaseError, "file is not a database"):
        conn = sqlite3.connect(db)
        try:
            conn.execute("SELECT name FROM sqlite_master").fetchall()
        finally:
            conn.close()


def read_encrypted_library(db: Path) -> RekordboxLibrary:
    return read_rekordbox_master_db(db, key=rekordbox_public_sqlcipher_key())


def read_encrypted_master_copy(source: Path, target: Path) -> RekordboxLibrary:
    shutil.copy2(source, target)
    return read_encrypted_library(target)


@contextlib.contextmanager
def rekordbox_not_running():
    from pyrekordbox.db6 import database

    original_get_pid = database.get_rekordbox_pid
    database.get_rekordbox_pid = lambda: 0
    try:
        yield
    finally:
        database.get_rekordbox_pid = original_get_pid
