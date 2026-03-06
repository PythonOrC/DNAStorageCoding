from __future__ import annotations

from collections import Counter
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

    def decode(self, codeword: bytes, erase_pos: Optional[list[int]] = None) -> Optional[bytes]:
        if self._rs is None:
            if len(codeword) < self.parity_bytes:
                return None
            return codeword[:-self.parity_bytes]
        try:
            if erase_pos:
                decoded = self._rs.decode(codeword, erase_pos=erase_pos)
            else:
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
        self.max_codeword_bytes = len(self.rs.encode(b"\x00" * self.chunk_data_bytes))

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

    def _strip_markers(self, dna: str, phase: int) -> tuple[str, list[int]]:
        if self.marker_period <= 0:
            return dna, []
        marker_len = len(self.marker)
        pos = 0
        out: list[str] = []
        uncertain_data_base_positions: list[int] = []
        data_base_cursor = 0
        first = max(1, self.marker_period - (phase % self.marker_period))
        seg_len = first
        while pos < len(dna):
            take = min(seg_len, len(dna) - pos)
            out.append(dna[pos : pos + take])
            data_base_cursor += take
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
                data_base_cursor += len(dna[pos:])
                break
            # Marker boundary was fuzzy; track this region as uncertain.
            uncertain_data_base_positions.append(data_base_cursor)
            if marker_pos > pos:
                out.append(dna[pos:marker_pos])
                data_base_cursor += marker_pos - pos
            pos = marker_pos + marker_len
        return "".join(out), uncertain_data_base_positions

    def _strip_markers_exact(self, dna: str, phase: int) -> str:
        """Exact marker stripping for non-indel paths."""
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
            if dna[pos : pos + marker_len] != self.marker:
                raise ValueError("exact marker not found")
            pos += marker_len
        return "".join(out)

    def _gc_reset_positions_for_phase(self, total_trits: int, phase: int) -> set[int]:
        first = max(1, self.marker_period - (phase % self.marker_period))
        positions: set[int] = set()
        p = first
        while p < total_trits:
            positions.add(p)
            p += self.marker_period
        return positions

    def _strip_markers_to_segments_exact(self, dna: str, phase: int) -> tuple[list[str], list[int]]:
        """Strip markers and return (segments, uncertain_segment_indices).

        In the exact-marker path, segment boundaries are deterministic. If a
        non-terminal segment has a length mismatch versus the expected period,
        mark it as uncertain so downstream decode can treat it as erasures.
        """
        if self.marker_period <= 0:
            return [dna], []
        marker_len = len(self.marker)
        pos = 0
        segments: list[str] = []
        uncertain_segments: list[int] = []
        first = max(1, self.marker_period - (phase % self.marker_period))
        seg_len = first
        seg_idx = 0
        while pos < len(dna):
            take = min(seg_len, len(dna) - pos)
            segment = dna[pos : pos + take]
            segments.append(segment)
            pos += take
            is_terminal = pos >= len(dna)
            if not is_terminal and len(segment) != seg_len:
                uncertain_segments.append(seg_idx)
            seg_len = self.marker_period
            if is_terminal:
                break
            if dna[pos : pos + marker_len] != self.marker:
                raise ValueError("exact marker not found")
            pos += marker_len
            seg_idx += 1
        return segments, uncertain_segments

    def _strip_markers_to_segments(self, dna: str, phase: int) -> tuple[list[str], list[int]]:
        """Strip markers with fuzzy matching; return segments + uncertain segment indices."""
        if self.marker_period <= 0:
            return [dna], []
        marker_len = len(self.marker)
        pos = 0
        segments: list[str] = []
        uncertain_segments: list[int] = []
        first = max(1, self.marker_period - (phase % self.marker_period))
        seg_len = first
        seg_idx = 0
        while pos < len(dna):
            seg_start = pos
            take = min(seg_len, len(dna) - pos)
            segment = dna[seg_start : seg_start + take]
            pos += take
            is_terminal = pos >= len(dna)
            if not is_terminal and len(segment) != seg_len:
                uncertain_segments.append(seg_idx)
            seg_len = self.marker_period
            if is_terminal:
                segments.append(segment)
                break
            if dna[pos : pos + marker_len] == self.marker:
                segments.append(segment)
                pos += marker_len
                seg_idx += 1
                continue
            marker_pos = self._find_marker_near(dna, pos)
            if marker_pos is None:
                segments.append(dna[seg_start:])
                uncertain_segments.append(seg_idx)
                break
            uncertain_segments.append(seg_idx)
            segments.append(dna[seg_start:marker_pos])
            pos = marker_pos + marker_len
            seg_idx += 1
        return segments, uncertain_segments

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
            chunk = header + header + codeword
            total_trits = len(chunk) * 6
            for replica_id in range(self.replication):
                gc_resets = self._gc_reset_positions_for_phase(total_trits, phase=replica_id)
                dna_core = self._constrained.encode_bytes_constrained(chunk, gc_reset_positions=gc_resets)
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

    # ------------------------------------------------------------------
    # Two-phase decode: extract raw codeword, then RS + CRC verify
    # ------------------------------------------------------------------

    def _decode_to_codeword(self, strand: ObservedStrand) -> Optional[tuple[dict, bytes, list[int]]]:
        """Phase 1: marker strip + constrained decode + header parse.

        Returns (header_dict, codeword_bytes, cw_erasure_positions) or None.
        """
        uncertain_segments: list[int] = []
        try:
            segments, uncertain_segments = self._strip_markers_to_segments_exact(
                strand.dna, phase=strand.replica_id
            )
        except Exception:
            segments, uncertain_segments = self._strip_markers_to_segments(
                strand.dna, phase=strand.replica_id
            )

        header_bytes_total = HEADER_SIZE * 2
        total_seg_bases = sum(len(s) for s in segments)
        max_decodable_bytes = total_seg_bases // 6
        decode_budget = min(header_bytes_total + self.max_codeword_bytes, max_decodable_bytes)
        if decode_budget < header_bytes_total + 1:
            return None

        decoded_max, erasure_bytes = self._constrained.decode_segments_resilient(
            segments, expected_bytes=decode_budget, uncertain_segments=uncertain_segments,
        )

        h1_raw = decoded_max[:HEADER_SIZE]
        h2_raw = decoded_max[HEADER_SIZE : HEADER_SIZE * 2]
        h1 = None
        h2 = None
        try:
            h1 = unpack_header(h1_raw)
        except Exception:
            pass
        try:
            h2 = unpack_header(h2_raw)
        except Exception:
            pass
        header = None
        if h1 is not None and h2 is not None:
            if h1 == h2:
                header = h1
            else:
                cands = [x for x in (h1, h2) if 1 <= x["data_len"] <= self.max_codeword_bytes]
                header = cands[0] if cands else None
        elif h1 is not None:
            header = h1
        elif h2 is not None:
            header = h2
        if header is None:
            return None

        codeword_len = header["data_len"]
        if codeword_len <= 0 or codeword_len > self.max_codeword_bytes:
            return None
        codeword = decoded_max[header_bytes_total : header_bytes_total + codeword_len]

        cw_erasures: set[int] = set()
        for byte_idx in erasure_bytes:
            cw_idx = byte_idx - header_bytes_total
            if 0 <= cw_idx < codeword_len:
                cw_erasures.add(cw_idx)

        if len(codeword) < codeword_len:
            for k in range(len(codeword), codeword_len):
                cw_erasures.add(k)
            codeword = codeword + b"\x00" * (codeword_len - len(codeword))

        return header, codeword, sorted(cw_erasures)

    def _rs_decode_and_verify(self, header: dict, codeword: bytes, erasures: list[int]) -> Optional[DecodedChunk]:
        """Phase 2: RS decode + CRC check."""
        erase_pos = erasures if erasures else None
        payload = self.rs.decode(codeword, erase_pos=erase_pos)
        if payload is None:
            return None
        valid = crc32_bytes(payload) == header["crc32_data"]
        return DecodedChunk(chunk_id=header["chunk_id"], data=payload, valid_crc=valid)

    @staticmethod
    def _vote_codewords(
        infos: list[tuple[dict, bytes, list[int]]],
    ) -> tuple[dict, bytes, list[int]]:
        """Byte-level majority vote across replica codewords."""
        if len(infos) == 1:
            return infos[0]
        header = infos[0][0]
        max_len = max(len(cw) for _, cw, _ in infos)
        erase_sets = [set(er) for _, _, er in infos]
        voted = bytearray(max_len)
        voted_erasures: list[int] = []
        for pos in range(max_len):
            candidates: list[int] = []
            for i, (_, cw, _) in enumerate(infos):
                if pos < len(cw) and pos not in erase_sets[i]:
                    candidates.append(cw[pos])
            if candidates:
                voted[pos] = Counter(candidates).most_common(1)[0][0]
            else:
                voted[pos] = 0
                voted_erasures.append(pos)
        return header, bytes(voted), voted_erasures

    def _decode_one(self, strand: ObservedStrand) -> Optional[DecodedChunk]:
        info = self._decode_to_codeword(strand)
        if info is None:
            return None
        return self._rs_decode_and_verify(*info)

    def decode_strands(self, strands: list[ObservedStrand]) -> DecodeResult:
        out: dict[int, DecodedChunk] = {}
        failures = 0
        total_chunks_expected = 0
        by_chunk: dict[int, list[ObservedStrand]] = {}
        for strand in strands:
            by_chunk.setdefault(strand.chunk_id, []).append(strand)
        for chunk_id, chunk_strands in by_chunk.items():
            cw_infos: list[tuple[dict, bytes, list[int]]] = []
            crc_ok: list[DecodedChunk] = []
            for strand in chunk_strands:
                try:
                    info = self._decode_to_codeword(strand)
                    if info is None:
                        failures += 1
                        continue
                    hdr, cw, er = info
                    if hdr["chunk_id"] != chunk_id:
                        failures += 1
                        continue
                    cw_infos.append(info)
                    decoded = self._rs_decode_and_verify(hdr, cw, er)
                    if decoded is not None and decoded.valid_crc:
                        crc_ok.append(decoded)
                except Exception:
                    failures += 1

            if crc_ok:
                pvotes = Counter(c.data for c in crc_ok)
                best_payload, _ = pvotes.most_common(1)[0]
                out[chunk_id] = DecodedChunk(chunk_id=chunk_id, data=best_payload, valid_crc=True)
                total_chunks_expected = max(total_chunks_expected, chunk_id + 1)
                continue

            # Fallback: byte-level vote across replicas, then RS decode.
            if len(cw_infos) >= 2:
                voted_hdr, voted_cw, voted_er = self._vote_codewords(cw_infos)
                decoded = self._rs_decode_and_verify(voted_hdr, voted_cw, voted_er)
                if decoded is not None and decoded.valid_crc:
                    out[chunk_id] = DecodedChunk(chunk_id=chunk_id, data=decoded.data, valid_crc=True)
                    total_chunks_expected = max(total_chunks_expected, chunk_id + 1)

        return DecodeResult(chunks=out, total_chunks_expected=total_chunks_expected, failures=failures)




