from __future__ import annotations

import struct

from .utils_bits import crc32_bytes


MAGIC = b"DNAS"
VERSION = 1
HEADER_STRUCT = struct.Struct(">4sBBBIIHII")
HEADER_SIZE = HEADER_STRUCT.size


def pack_header(
    scheme_byte: int,
    chunk_id: int,
    total_chunks: int,
    data_len: int,
    bit_len: int,
    crc32_data: int,
    reserved: int = 0,
) -> bytes:
    return HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        scheme_byte,
        reserved,
        chunk_id,
        total_chunks,
        data_len,
        bit_len,
        crc32_data,
    )


def unpack_header(buf: bytes) -> dict:
    if len(buf) < HEADER_SIZE:
        raise ValueError("buffer too short for header")
    magic, version, scheme_byte, reserved, chunk_id, total_chunks, data_len, bit_len, crc = (
        HEADER_STRUCT.unpack(buf[:HEADER_SIZE])
    )
    if magic != MAGIC:
        raise ValueError("invalid magic")
    if version != VERSION:
        raise ValueError("unsupported version")
    return {
        "scheme_byte": scheme_byte,
        "reserved": reserved,
        "chunk_id": chunk_id,
        "total_chunks": total_chunks,
        "data_len": data_len,
        "bit_len": bit_len,
        "crc32_data": crc,
    }


def build_chunk_bytes(
    scheme_byte: int,
    chunk_id: int,
    total_chunks: int,
    payload: bytes,
    bit_len: int = 0,
    reserved: int = 0,
) -> bytes:
    header = pack_header(
        scheme_byte=scheme_byte,
        chunk_id=chunk_id,
        total_chunks=total_chunks,
        data_len=len(payload),
        bit_len=bit_len,
        crc32_data=crc32_bytes(payload),
        reserved=reserved,
    )
    return header + payload
