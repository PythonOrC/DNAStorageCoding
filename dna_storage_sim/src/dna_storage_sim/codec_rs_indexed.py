from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .codec_base import Codec, DecodeResult, DecodedChunk, EncodedStrand, ObservedStrand
from .codec_constrained import ConstrainedCodec
from .chunk_format import HEADER_SIZE, pack_header, unpack_header
from .utils_bits import crc32_bytes

try:
    from reedsolo import RSCodec  # type: ignore
except Exception:  # pragma: no cover
    RSCodec = None


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]


@dataclass
class RSWrapper:
    parity_bytes: int

    def __post_init__(self) -> None:
        self._rs = RSCodec(self.parity_bytes) if RSCodec is not None else None

    def encode(self, payload: bytes) -> bytes:
        if self._rs is None:
            return payload + (b"\x00" * self.parity_bytes)
        return bytes(self._rs.encode(payload))

    def decode(self, codeword: bytes) -> Optional[bytes]:
        if self._rs is None:
            if len(codeword) < self.parity_bytes:
                return None
            return codeword[:-self.parity_bytes]
        try:
            decoded = self._rs.decode(codeword)
            if isinstance(decoded, tuple):
                decoded = decoded[0]
            return bytes(decoded)
        except Exception:
            return None


class RSIndexedCodec(Codec):
    scheme_id = "s3"
    scheme_byte = 3

    def __init__(
        self,
        chunk_data_bytes: int = 1024,
        gc_target: float = 0.5,
        rs_parity_bytes: int = 32,
        marker: str = "ACGTACGTAC",
        marker_period: int = 40,
        max_marker_edit_distance: int = 2,
        replication: int = 2,
    ):
        self.chunk_data_bytes = chunk_data_bytes
        self.gc_target = gc_target
        self.rs = RSWrapper(rs_parity_bytes)
        self.parity_bytes = rs_parity_bytes
        self.marker = marker
        self.marker_period = marker_period
        self.max_marker_edit_distance = max_marker_edit_distance
        self.replication = replication
        self._constrained = ConstrainedCodec(chunk_data_bytes=chunk_data_bytes, gc_target=gc_target)

    def _insert_markers(self, dna: str, phase: int) -> str:
        if self.marker_period <= 0:
            return dna
        out: list[str] = []
        i = 0
        first = max(1, self.marker_period - (phase % self.marker_period))
        while i < len(dna):
            step = first if i == 0 else self.marker_period
            out.append(dna[i : i + step])
            i += step
            if i < len(dna):
                out.append(self.marker)
        return "".join(out)

    def _find_marker_near(self, dna: str, expected_start: int) -> Optional[int]:
        marker_len = len(self.marker)
        left = max(0, expected_start - self.max_marker_edit_distance)
        right = min(len(dna) - marker_len, expected_start + self.max_marker_edit_distance)
        if right < left:
            return None
        exact = dna.find(self.marker, left, right + marker_len + 1)
        if exact != -1:
            return exact
        best_pos = None
        best_dist = self.max_marker_edit_distance + 1
        for pos in range(left, right + 1):
            cand = dna[pos : pos + marker_len]
            if len(cand) != marker_len:
                continue
            dist = _levenshtein(cand, self.marker)
            if dist < best_dist:
                best_dist = dist
                best_pos = pos
        if best_dist <= self.max_marker_edit_distance:
            return best_pos
        return None

    def _strip_markers(self, dna: str, phase: int) -> str:
        if self.marker_period <= 0:
            return dna
        marker_len = len(self.marker)
        pos = 0
        out: list[str] = []
        first = max(1, self.marker_period - (phase % self.marker_period))
        seg_len = first
        while pos < len(dna):
            take = min(seg_len, len(dna) - pos)
            out.append(dna[pos : pos + take])
            pos += take
            seg_len = self.marker_period
            if pos >= len(dna):
                break
            if dna[pos : pos + marker_len] == self.marker:
                pos += marker_len
                continue
            marker_pos = self._find_marker_near(dna, pos)
            if marker_pos is None:
                out.append(dna[pos:])
                break
            if marker_pos > pos:
                out.append(dna[pos:marker_pos])
            pos = marker_pos + marker_len
        return "".join(out)

    def encode_file(self, data: bytes) -> list[EncodedStrand]:
        total_chunks = (len(data) + self.chunk_data_bytes - 1) // self.chunk_data_bytes
        strands: list[EncodedStrand] = []
        for chunk_id in range(total_chunks):
            start = chunk_id * self.chunk_data_bytes
            payload = data[start : start + self.chunk_data_bytes]
            bit_len = len(payload) * 8
            codeword = self.rs.encode(payload)
            header = pack_header(
                scheme_byte=self.scheme_byte,
                chunk_id=chunk_id,
                total_chunks=total_chunks,
                data_len=len(codeword),
                bit_len=bit_len,
                crc32_data=crc32_bytes(payload),
            )
            chunk = header + codeword
            dna_core = self._constrained.encode_bytes_constrained(chunk)
            for replica_id in range(self.replication):
                dna = self._insert_markers(dna_core, phase=replica_id)
                strands.append(
                    EncodedStrand(
                        scheme_id=self.scheme_id,
                        chunk_id=chunk_id,
                        replica_id=replica_id,
                        dna=dna,
                        bases_total=len(dna),
                        meta={"payload_len": len(payload)},
                    )
                )
        return strands

    def _decode_one(self, strand: ObservedStrand) -> Optional[DecodedChunk]:
        core = self._strip_markers(strand.dna, phase=strand.replica_id)
        header_bytes = self._constrained.decode_bytes_constrained(core, expected_bytes=HEADER_SIZE)
        header = unpack_header(header_bytes[:HEADER_SIZE])
        total_bytes = HEADER_SIZE + header["data_len"]
        decoded = self._constrained.decode_bytes_constrained(core, expected_bytes=total_bytes)
        header = unpack_header(decoded[:HEADER_SIZE])
        codeword = decoded[HEADER_SIZE : HEADER_SIZE + header["data_len"]]
        payload = self.rs.decode(codeword)
        if payload is None:
            return None
        if crc32_bytes(payload) != header["crc32_data"]:
            return None
        return DecodedChunk(chunk_id=header["chunk_id"], data=payload, valid_crc=True)

    def decode_strands(self, strands: list[ObservedStrand]) -> DecodeResult:
        out: dict[int, DecodedChunk] = {}
        failures = 0
        total_chunks_expected = 0
        for strand in strands:
            if strand.chunk_id in out:
                continue
            try:
                decoded = self._decode_one(strand)
                if decoded is None:
                    failures += 1
                    continue
                out[decoded.chunk_id] = decoded
                total_chunks_expected = max(total_chunks_expected, decoded.chunk_id + 1)
            except Exception:
                failures += 1
        return DecodeResult(chunks=out, total_chunks_expected=total_chunks_expected, failures=failures)
