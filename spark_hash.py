# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Dependency-free XXH64 (xxHash 64-bit, oneshot).

Little-endian XXH64 as published by Yann Collet: four 64-bit accumulators
over 32-byte stripes, merge rounds, an 8/4/1-byte tail, then the avalanche.
Every add and multiply is masked to 64 bits. ``seed`` is reduced modulo
2**64; a negative seed wraps as two's complement, matching the C ``uint64_t``
argument.

``spark_id.py`` imports ``xxh64_hexdigest`` from here. The only imports are
the standard library. Lanes are read from a ``memoryview`` with
``struct.unpack_from`` (stripes) and ``int.from_bytes`` (the short tail).

Run ``python3 spark_hash.py`` to hash raw stdin (seed 0) and print 16
lowercase hex digits plus a newline.
"""

import struct
import sys

_MASK64 = 0xFFFFFFFFFFFFFFFF

# XXH_PRIME64_1 .. XXH_PRIME64_5 from the xxHash specification.
_PRIME64_1 = 0x9E3779B185EBCA87
_PRIME64_2 = 0xC2B2AE3D27D4EB4F
_PRIME64_3 = 0x165667B19E3779F9
_PRIME64_4 = 0x85EBCA77C2B2AE63
_PRIME64_5 = 0x27D4EB2F165667C5

_STRIPE_BYTES = 32
# Four little-endian lanes. One unpack avoids a Python slice per lane.
_STRIPE = struct.Struct("<QQQQ")


def _rotl64(value: int, bits: int) -> int:
    return ((value << bits) | (value >> (64 - bits))) & _MASK64


def _round64(acc: int, lane: int) -> int:
    """XXH64_round: acc += lane * P2; rotl 31; acc *= P1."""
    acc = (acc + lane * _PRIME64_2) & _MASK64
    return (_rotl64(acc, 31) * _PRIME64_1) & _MASK64


def _merge_round(acc: int, lane: int) -> int:
    """XXH64_mergeRound: acc ^= round(0, lane); acc = acc * P1 + P4."""
    acc ^= _round64(0, lane)
    return (acc * _PRIME64_1 + _PRIME64_4) & _MASK64


def _u32(view: memoryview, offset: int) -> int:
    return int.from_bytes(view[offset : offset + 4], "little")


def _u64(view: memoryview, offset: int) -> int:
    return int.from_bytes(view[offset : offset + 8], "little")


def xxh64(data: bytes, seed: int = 0) -> int:
    """Return the XXH64 digest of ``data`` as an unsigned 64-bit integer.

    ``data`` may be any bytes-like object; its raw bytes are hashed (a
    non-byte or noncontiguous buffer is copied to ``bytes`` first).
    """
    view = memoryview(data)
    if view.format != "B" or view.ndim != 1 or not view.contiguous:
        view = memoryview(view.tobytes())
    length = len(view)
    seed &= _MASK64
    prime1 = _PRIME64_1
    prime2 = _PRIME64_2
    prime3 = _PRIME64_3
    prime4 = _PRIME64_4
    prime5 = _PRIME64_5
    mask = _MASK64

    if length >= _STRIPE_BYTES:
        # seed+P1+P2, seed+P2, seed, seed-P1. Each lane then eats 8 bytes.
        acc1 = (seed + prime1 + prime2) & mask
        acc2 = (seed + prime2) & mask
        acc3 = seed
        acc4 = (seed - prime1) & mask
        unpack_stripe = _STRIPE.unpack_from
        offset = 0
        stripe_end = length - (length % _STRIPE_BYTES)
        while offset < stripe_end:
            lane1, lane2, lane3, lane4 = unpack_stripe(view, offset)
            # Inlined _round64 so the hot loop does not call per lane.
            mixed = (acc1 + lane1 * prime2) & mask
            acc1 = (((mixed << 31) | (mixed >> 33)) * prime1) & mask
            mixed = (acc2 + lane2 * prime2) & mask
            acc2 = (((mixed << 31) | (mixed >> 33)) * prime1) & mask
            mixed = (acc3 + lane3 * prime2) & mask
            acc3 = (((mixed << 31) | (mixed >> 33)) * prime1) & mask
            mixed = (acc4 + lane4 * prime2) & mask
            acc4 = (((mixed << 31) | (mixed >> 33)) * prime1) & mask
            offset += _STRIPE_BYTES
        digest = (
            _rotl64(acc1, 1) + _rotl64(acc2, 7) + _rotl64(acc3, 12) + _rotl64(acc4, 18)
        ) & mask
        digest = _merge_round(digest, acc1)
        digest = _merge_round(digest, acc2)
        digest = _merge_round(digest, acc3)
        digest = _merge_round(digest, acc4)
    else:
        digest = (seed + prime5) & mask
        offset = 0

    digest = (digest + length) & mask

    # Tail is the unread suffix, at most 31 bytes: 8-byte, then 4-byte, then bytes.
    while offset + 8 <= length:
        key = _round64(0, _u64(view, offset))
        digest ^= key
        digest = (_rotl64(digest, 27) * prime1 + prime4) & mask
        offset += 8

    if offset + 4 <= length:
        digest ^= (_u32(view, offset) * prime1) & mask
        digest = (_rotl64(digest, 23) * prime2 + prime3) & mask
        offset += 4

    while offset < length:
        digest ^= (view[offset] * prime5) & mask
        digest = (_rotl64(digest, 11) * prime1) & mask
        offset += 1

    # Avalanche.
    digest ^= digest >> 33
    digest = (digest * prime2) & mask
    digest ^= digest >> 29
    digest = (digest * prime3) & mask
    digest ^= digest >> 32
    return digest


def xxh64_hexdigest(data: bytes, seed: int = 0) -> str:
    """Return ``xxh64(data, seed)`` as 16 lowercase hex characters, zero-padded."""
    return f"{xxh64(data, seed):016x}"


def main() -> int:
    """Hash raw stdin with seed 0 and write the hex digest plus a newline."""
    sys.stdout.write(xxh64_hexdigest(sys.stdin.buffer.read()))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
