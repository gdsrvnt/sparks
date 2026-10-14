# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8"]
# ///

"""XXH64 reference vectors for spark_hash.py.

Official rows are the XXH64 table in Cyan4973/xxHash ``cli/xsum_sanity_check.c``
(``XSUM_XXH64_testdata``). Their inputs are ``XSUM_fillTestBuffer``, not the
string itself: ``byteGen`` starts at PRIME32 (2654435761), each byte is
``byteGen >> 56``, then ``byteGen *= PRIME64`` (11400714785074694797), all
mod 2**64.

Other rows were produced by python-xxhash 4.0.1, which links XXHASH 0.8.3,
via ``uv run --with xxhash``. That package is not a test or runtime dependency;
the expected digests are hardcoded. ``spark_hash.py`` is loaded by path.
"""

import ast
import importlib.machinery
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HASH_PATH = ROOT / "spark_hash.py"

_PRIME32 = 2654435761
_PRIME64 = 11400714785074694797
_MASK64 = 0xFFFFFFFFFFFFFFFF


def _load_spark_hash():
    """Load the repo-root implementation by path, not by sys.path import."""
    loader = importlib.machinery.SourceFileLoader("spark_hash_by_path", str(HASH_PATH))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


spark_hash = _load_spark_hash()
xxh64 = spark_hash.xxh64
xxh64_hexdigest = spark_hash.xxh64_hexdigest


def official_buffer(length: int) -> bytes:
    """Reproduce ``XSUM_fillTestBuffer`` from the xxHash sanity check."""
    buffer = bytearray(length)
    byte_gen = _PRIME32
    for index in range(length):
        buffer[index] = (byte_gen >> 56) & 0xFF
        byte_gen = (byte_gen * _PRIME64) & _MASK64
    return bytes(buffer)


# len, seed, hex digest. Seed PRIME32 is the 32-bit prime, not PRIME64_1.
OFFICIAL = (
    pytest.param(0, 0, "ef46db3751d8e999", id="len0-seed0"),
    pytest.param(0, _PRIME32, "ac75fda2929b17ef", id="len0-prime32"),
    pytest.param(1, 0, "e934a84adb052768", id="len1-seed0"),
    pytest.param(1, _PRIME32, "5014607643a9b4c3", id="len1-prime32"),
    pytest.param(4, 0, "9136a0dca57457ee", id="len4-seed0"),
    pytest.param(14, 0, "8282dcc4994e35c8", id="len14-seed0"),
    pytest.param(14, _PRIME32, "c3bd6bf63deb6df0", id="len14-prime32"),
    pytest.param(222, 0, "b641ae8cb691c174", id="len222-seed0"),
    pytest.param(222, _PRIME32, "20cb8ab7ae10c14a", id="len222-prime32"),
)

# (data, seed, hex). Checked against python-xxhash / XXH 0.8.3.
VERIFIED = (
    pytest.param(b"a", 0, "d24ec4f1a98c6e5b", id="a"),
    pytest.param(b"abc", 0, "44bc2cf5ad770999", id="abc"),
    pytest.param(b"abc", 42, "13c1d910702770e6", id="abc-seed42"),
    pytest.param(b"\x18\x00", 0, "0c465f3dd948930f", id="leading-zero-hex"),
    pytest.param(b"\x00" * 31, 0, "faf43dd52deb083a", id="zeros31"),
    pytest.param(b"\x00" * 32, 0, "f6e9be5d70632cf5", id="zeros32"),
    pytest.param(b"\x00" * 33, 0, "1dcdf75a2320fb61", id="zeros33"),
    pytest.param(b"\x00" * 63, 0, "d81772f2c42d7324", id="zeros63"),
    pytest.param(b"\x00" * 64, 0, "257b09a147b82a19", id="zeros64"),
    pytest.param(b"0123456789abcdef" * 2, 0, "642a94958e71e6c5", id="ascii32"),
    pytest.param(b"0123456789abcdef" * 2, 42, "666b1f69d2455da5", id="ascii32-seed42"),
    pytest.param(
        b"The quick brown fox jumps over the lazy dog",
        0,
        "0b242d361fda71bc",
        id="fox",
    ),
    pytest.param(b"a\x00b\x00c" * 10, 0, "c38308d5fbdef004", id="interior-nulls"),
    pytest.param(b"\x00" * 1024, 0, "27742888f085accd", id="zeros1024"),
    pytest.param(bytes(range(256)) * 4, 0, "6f3914f18fe4df57", id="seq1024"),
    pytest.param(b"\xff" * 100, 2**64 - 1, "471be9818268e261", id="ff100-maxseed"),
)


@pytest.mark.parametrize("length,seed,expected", OFFICIAL)
def test_official_reference_vectors(length: int, seed: int, expected: str) -> None:
    data = official_buffer(length)
    assert xxh64_hexdigest(data, seed) == expected
    assert xxh64(data, seed) == int(expected, 16)


@pytest.mark.parametrize("data,seed,expected", VERIFIED)
def test_vectors_checked_against_xxhash(data: bytes, seed: int, expected: str) -> None:
    assert xxh64_hexdigest(data, seed) == expected
    assert xxh64(data, seed) == int(expected, 16)


def test_seed_masks_to_64_bits() -> None:
    """python-xxhash accepts these seeds and returns the same digests."""
    assert xxh64(b"a", -1) == xxh64(b"a", 2**64 - 1) == 0x60C43759873ECE62
    assert xxh64(b"abc", -42) == xxh64(b"abc", 2**64 - 42) == 0x1BA9C0759663B7E3
    assert xxh64(b"abc", 42 + 2**64) == xxh64(b"abc", 42) == 0x13C1D910702770E6
    assert xxh64(b"0123456789abcdef" * 2, 42 + (1 << 64)) == 0x666B1F69D2455DA5


def test_module_imports_only_the_standard_library() -> None:
    tree = ast.parse(HASH_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported <= {"struct", "sys"}
    assert "ctypes" not in imported
    assert "subprocess" not in imported


def test_script_header_declares_no_dependencies() -> None:
    text = HASH_PATH.read_text(encoding="utf-8")
    assert text.startswith("# /// script\n")
    assert 'requires-python = ">=3.11"' in text.split("# ///", 2)[1]
    assert "dependencies = []" in text.split("# ///", 2)[1]


@pytest.mark.parametrize(
    "payload,expected",
    (
        pytest.param(b"", "ef46db3751d8e999", id="empty"),
        pytest.param(b"a", "d24ec4f1a98c6e5b", id="a"),
        pytest.param(b"abc", "44bc2cf5ad770999", id="abc"),
        pytest.param(b"0123456789abcdef" * 2, "642a94958e71e6c5", id="ascii32"),
        pytest.param(b"a\x00b\x00c" * 10, "c38308d5fbdef004", id="nulls"),
    ),
)
def test_cli_reads_stdin_and_prints_hex_digest(payload: bytes, expected: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(HASH_PATH)],
        input=payload,
        capture_output=True,
        cwd=ROOT,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout == expected.encode("ascii") + b"\n"
    assert completed.stderr == b""



if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-p", "no:cacheprovider", *sys.argv[1:]]))
