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
