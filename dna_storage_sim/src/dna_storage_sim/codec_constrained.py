from __future__ import annotations

from .codec_base import Codec, DecodeResult, DecodedChunk, EncodedStrand, ObservedStrand
from .chunk_format import HEADER_SIZE, build_chunk_bytes, unpack_header
from .utils_bits import crc32_bytes


BASES = ("A", "C", "G", "T")

ORDER0 = {
    "A": ("C", "G", "T"),
    "C": ("A", "G", "T"),
    "G": ("A", "C", "T"),
    "T": ("A", "C", "G"),
}
ORDER1 = {
    "A": ("G", "C", "T"),
    "C": ("G", "A", "T"),
    "G": ("C", "A", "T"),
    "T": ("C", "A", "G"),
}


def choose_order(prev_base: str, gc_count: int, pos: int, gc_target: float) -> tuple[str, str, str]:
    expected_gc = gc_target * (pos + 1)
    if gc_count < expected_gc:
        return ORDER1[prev_base]
    return ORDER0[prev_base]


class ConstrainedCodec(Codec):
    scheme_id = "s2"
    scheme_byte = 2

    def __init__(self, chunk_data_bytes: int = 1024, gc_target: float = 0.5):
        self.chunk_data_bytes = chunk_data_bytes
        self.gc_target = gc_target

    @staticmethod
    def _bytes_to_trits_fixed(payload: bytes) -> list[int]:
        trits: list[int] = []
        for b in payload:
            n = b
            local = [0] * 6
            for i in range(5, -1, -1):
                n, r = divmod(n, 3)
                local[i] = r
            trits.extend(local)
        return trits

    @staticmethod
    def _trits_to_bytes_fixed(trits: list[int]) -> bytes:
        if len(trits) % 6 != 0:
            raise ValueError("invalid trit length")
        out = bytearray()
        for i in range(0, len(trits), 6):
            n = 0
            for t in trits[i : i + 6]:
                n = n * 3 + t
            if n > 255:
                raise ValueError("trit symbol out of byte range")
            out.append(n)
        return bytes(out)

    def encode_bytes_constrained(self, payload: bytes) -> str:
        trits = self._bytes_to_trits_fixed(payload)
        prev = "A"
        gc_count = 0
        dna_out: list[str] = []
        for i, t in enumerate(trits):
            order = choose_order(prev, gc_count, i, self.gc_target)
            base = order[t]
            dna_out.append(base)
            if base in ("G", "C"):
                gc_count += 1
            prev = base
        return "".join(dna_out)

    def decode_bytes_constrained(self, dna: str, expected_bytes: int) -> bytes:
        if not dna:
            return b""
        needed = expected_bytes * 6
        if len(dna) < needed:
            raise ValueError("dna shorter than expected payload")
        trits: list[int] = []
        prev = "A"
        gc_count = 0
        for i, base in enumerate(dna[:needed]):
            order = choose_order(prev, gc_count, i, self.gc_target)
            try:
                trit = order.index(base)
            except ValueError as exc:
                raise ValueError("invalid constrained symbol") from exc
            trits.append(trit)
            if base in ("G", "C"):
                gc_count += 1
            prev = base
        return self._trits_to_bytes_fixed(trits)

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
            dna = self.encode_bytes_constrained(chunk)
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
                header_bytes = self.decode_bytes_constrained(strand.dna, expected_bytes=HEADER_SIZE)
                header = unpack_header(header_bytes[:HEADER_SIZE])
                total_bytes = HEADER_SIZE + header["data_len"]
                decoded = self.decode_bytes_constrained(strand.dna, expected_bytes=total_bytes)
                header = unpack_header(decoded[:HEADER_SIZE])
                payload = decoded[HEADER_SIZE : HEADER_SIZE + header["data_len"]]
                total_chunks_expected = max(total_chunks_expected, header["total_chunks"])
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
