from __future__ import annotations

import base64
import shutil
import unittest
import zlib
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.support.rekordbox_plain_fixture import build_plain_rekordbox_fixture_db

PUBLIC_KEY_BLOB = b"PN_Pq^*N>(JYe*u^8;Yg76HuZ<mR13S?=>)b9;DpoTXV(6ItkU`}8*m6tx_I{Solh_N#dfe{v="
BLOB_KEY = b"657f48f84c437cc1"
SQLCIPHER4_PRAGMAS = (
    "PRAGMA cipher_page_size = 4096",
    "PRAGMA kdf_iter = 256000",
    "PRAGMA cipher_hmac_algorithm = HMAC_SHA512",
    "PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512",
)


class SqlcipherUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class EncryptedRekordboxFixture:
    encrypted_db: Path
    plain_db: Path
    schema: str = "sqlcipher4"


def rekordbox_public_sqlcipher_key() -> str:
    data = base64.b85decode(PUBLIC_KEY_BLOB)
    xored = bytes(byte ^ BLOB_KEY[index % len(BLOB_KEY)] for index, byte in enumerate(data))
    return zlib.decompress(xored).decode("utf-8")


def skip_or_fail_for_missing_encrypted_backend(testcase: unittest.TestCase, exc: Exception) -> None:
    message = f"{exc}; install djlib-doctor with default dependencies before running the full local gate"
    if _djlib_doctor_is_installed():
        testcase.fail(message)
    testcase.skipTest(message)


def _djlib_doctor_is_installed() -> bool:
    try:
        version("djlib-doctor")
    except PackageNotFoundError:
        return False
    return True


def generate_encrypted_rekordbox_fixture(out_path: Path) -> EncryptedRekordboxFixture:
    sqlcipher = _sqlcipher()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    plain_copy = out_path.with_suffix(".plain.db")
    if plain_copy.exists():
        plain_copy.unlink()
    with TemporaryDirectory() as tmpdir:
        plain = Path(tmpdir) / "plain-master.db"
        build_plain_rekordbox_fixture_db(plain)
        shutil.copy2(plain, plain_copy)
        _encrypt_plain_db(sqlcipher, plain_copy, out_path)
    return EncryptedRekordboxFixture(out_path, plain_copy)


def _encrypt_plain_db(sqlcipher: object, plain: Path, encrypted: Path) -> None:
    conn = sqlcipher.connect(str(plain))
    try:
        key = rekordbox_public_sqlcipher_key().replace("'", "''")
        target = str(encrypted).replace("'", "''")
        conn.execute(f"ATTACH DATABASE '{target}' AS encrypted KEY '{key}'")
        for pragma in SQLCIPHER4_PRAGMAS:
            conn.execute(pragma.replace("PRAGMA ", "PRAGMA encrypted."))
        conn.execute("SELECT sqlcipher_export('encrypted')")
        conn.execute("DETACH DATABASE encrypted")
    finally:
        conn.close()


def _sqlcipher() -> object:
    try:
        from sqlcipher3 import dbapi2 as sqlcipher
    except ImportError as exc:
        raise SqlcipherUnavailable(
            "sqlcipher3 is unavailable; reinstall djlib-doctor with its default Rekordbox DB dependencies"
        ) from exc
    return sqlcipher
