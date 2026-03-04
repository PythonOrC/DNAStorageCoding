from __future__ import annotations

from .codec_base import Codec, DecodeResult, DecodedChunk, EncodedStrand, ObservedStrand
from .chunk_format import HEADER_SIZE, build_chunk_bytes, unpack_header
from .utils_bits import bits_to_bytes, bytes_to_bits, crc32_bytes


BIT_TO_BASE = {"00": "A", "01": "C", "10": "G", "11": "T"}
BASE_TO_BIT = {v: k for k, v in BIT_TO_BASE.items()}


class Naive2BitCodec(Codec):
    scheme_id = "s1"
    scheme_byte = 1

    def __init__(self, chunk_data_bytes: int = 1024):
        self.chunk_data_bytes = chunk_data_bytes

    @staticmethod
    def encode_bytes_to_dna_naive(data: bytes) -> str:
        bits = bytes_to_bits(data)
        if len(bits) % 2 != 0:
            bits += "0"
        return "".join(BIT_TO_BASE[bits[i : i + 2]] for i in range(0, len(bits), 2))

    @staticmethod
    def decode_dna_to_bytes_naive(dna: str) -> bytes:
        bits = []
        for b in dna:
            if b not in BASE_TO_BIT:
                raise ValueError("invalid base")
            bits.append(BASE_TO_BIT[b])
        return bits_to_bytes("".join(bits))

    def encode_file(self, data: bytes) -> list[EncodedStrand]:
        total_chunks = (len(data) + self.chunk_data_bytes - 1) // self.chunk_data_bytes
        strands: list[EncodedStrand] = []
        for chunk_id in range(total_chunks):
            start = chunk_id * self.chunk_data_bytes
            payload = data[start : start + self.chunk_data_bytes]
            chunk = build_chunk_bytes(
                scheme_byte=self.scheme_byte,
                chunk_id=chunk_id,
                total_chunks=total_chunks,
                payload=payload,
                bit_len=len(payload) * 8,
            )
            dna = self.encode_bytes_to_dna_naive(chunk)
            strands.append(
                EncodedStrand(
                    scheme_id=self.scheme_id,
                    chunk_id=chunk_id,
                    replica_id=0,
                    dna=dna,
                    bases_total=len(dna),
                    meta={"payload_len": len(payload)},
                )
            )
        return strands

    def decode_strands(self, strands: list[ObservedStrand]) -> DecodeResult:
        out: dict[int, DecodedChunk] = {}
        failures = 0
        total_chunks_expected = 0
        for strand in strands:
            if strand.chunk_id in out:
                continue
            try:
                decoded = self.decode_dna_to_bytes_naive(strand.dna)
                header = unpack_header(decoded[:HEADER_SIZE])
                total_chunks_expected = max(total_chunks_expected, header["total_chunks"])
                payload_start = HEADER_SIZE
                payload_end = payload_start + header["data_len"]
                payload = decoded[payload_start:payload_end]
                valid = crc32_bytes(payload) == header["crc32_data"]
                if valid:
                    out[header["chunk_id"]] = DecodedChunk(
                        chunk_id=header["chunk_id"], data=payload, valid_crc=True
                    )
                else:
                    failures += 1
            except Exception:
                failures += 1
        return DecodeResult(chunks=out, total_chunks_expected=total_chunks_expected, failures=failures)
