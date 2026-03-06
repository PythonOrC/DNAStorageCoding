from __future__ import annotations

import random

from dna_storage_sim.codec_base import ObservedStrand
from dna_storage_sim.codec_constrained import ConstrainedCodec
from dna_storage_sim.codec_naive import Naive2BitCodec
from dna_storage_sim.codec_rs_indexed import RSIndexedCodec
from dna_storage_sim.metrics import reassemble_bytes


def _make_bytes(n: int, seed: int) -> bytes:
    rng = random.Random(seed)
    return bytes(rng.getrandbits(8) for _ in range(n))


def _roundtrip(codec, data: bytes) -> bytes:
    encoded = codec.encode_file(data)
    observed = [
        ObservedStrand(
            scheme_id=s.scheme_id,
            chunk_id=s.chunk_id,
            replica_id=s.replica_id,
            dna=s.dna,
            bases_total=s.bases_total,
            meta=s.meta,
        )
        for s in encoded
    ]
    decoded = codec.decode_strands(observed)
    return reassemble_bytes(decoded)


def test_roundtrip_s1():
    codec = Naive2BitCodec(chunk_data_bytes=256)
    data = _make_bytes(4000, 11)
    out = _roundtrip(codec, data)
    assert out == data


def test_roundtrip_s2():
    codec = ConstrainedCodec(chunk_data_bytes=256, gc_target=0.5)
    data = _make_bytes(4000, 22)
    out = _roundtrip(codec, data)
    assert out == data


def test_roundtrip_s3():
    codec = RSIndexedCodec(chunk_data_bytes=256, rs_parity_bytes=16, marker_period=30, replication=2)
    data = _make_bytes(4000, 33)
    out = _roundtrip(codec, data)
    assert out == data


def test_s3_replica_voting_recovers_when_one_replica_bad():
    codec = RSIndexedCodec(chunk_data_bytes=256, rs_parity_bytes=16, marker_period=30, replication=2)
    data = _make_bytes(1024, 44)
    encoded = codec.encode_file(data)
    observed = []
    for s in encoded:
        dna = s.dna
        # Corrupt replica 0 to force failure while replica 1 remains decodable.
        if s.replica_id == 0 and len(dna) > 20:
            dna = "T" + dna[1:10] + "A" + dna[11:]
        observed.append(
            ObservedStrand(
                scheme_id=s.scheme_id,
                chunk_id=s.chunk_id,
                replica_id=s.replica_id,
                dna=dna,
                bases_total=s.bases_total,
                meta={"p_indel": 0.0},
            )
        )
    decoded = codec.decode_strands(observed)
    out = reassemble_bytes(decoded)
    assert out == data

def test_s3_segment_length_mismatch_marked_uncertain():
    codec = RSIndexedCodec(chunk_data_bytes=64, rs_parity_bytes=16, marker_period=12, replication=1)
    data = _make_bytes(256, 55)
    strand = codec.encode_file(data)[0]
    # Insert one base into the first segment before the first marker.
    mutated = strand.dna[:5] + "A" + strand.dna[5:]
    _, uncertain_segments = codec._strip_markers_to_segments(mutated, phase=strand.replica_id)
    assert 0 in uncertain_segments


def test_s3_segment_shift_produces_erasures_in_resilient_decode():
    codec = RSIndexedCodec(chunk_data_bytes=64, rs_parity_bytes=16, marker_period=12, replication=1)
    data = _make_bytes(256, 56)
    strand = codec.encode_file(data)[0]
    mutated = strand.dna[:5] + "A" + strand.dna[5:]

    segments, uncertain = codec._strip_markers_to_segments(mutated, phase=strand.replica_id)
    decoded_bytes, erasure_bytes = codec._constrained.decode_segments_resilient(
        segments, expected_bytes=64, uncertain_segments=uncertain
    )
    assert len(decoded_bytes) == 64
    assert len(erasure_bytes) > 0

