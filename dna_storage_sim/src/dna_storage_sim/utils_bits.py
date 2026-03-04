from __future__ import annotations

from typing import Iterable
import hashlib
import zlib


def crc32_bytes(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bytes_to_bits(data: bytes) -> str:
    return "".join(f"{b:08b}" for b in data)


def bits_to_bytes(bits: str, bit_len: int | None = None) -> bytes:
    if bit_len is None:
        bit_len = len(bits)
    bits = bits[:bit_len]
    if len(bits) % 8 != 0:
        bits = bits + ("0" * (8 - len(bits) % 8))
    if not bits:
        return b""
    return bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))


def bits_to_trits(bits: str) -> list[int]:
    if not bits:
        return [0]
    n = int(bits, 2)
    if n == 0:
        return [0]
    out: list[int] = []
    while n > 0:
        n, r = divmod(n, 3)
        out.append(r)
    out.reverse()
    return out


def trits_to_bits(trits: Iterable[int], bit_len: int) -> str:
    n = 0
    for t in trits:
        n = n * 3 + int(t)
    if bit_len == 0:
        return ""
    return f"{n:0{bit_len}b}"[-bit_len:]


def max_homopolymer_run(dna: str) -> int:
    if not dna:
        return 0
    max_run = 1
    run = 1
    for i in range(1, len(dna)):
        if dna[i] == dna[i - 1]:
            run += 1
            if run > max_run:
                max_run = run
        else:
            run = 1
    return max_run


def gc_fraction(dna: str) -> float:
    if not dna:
        return 0.0
    gc = sum(1 for b in dna if b in ("G", "C"))
    return gc / len(dna)
