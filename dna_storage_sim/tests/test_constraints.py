from __future__ import annotations

import random

from dna_storage_sim.codec_constrained import ConstrainedCodec
from dna_storage_sim.codec_rs_indexed import RSIndexedCodec
from dna_storage_sim.utils_bits import gc_fraction, max_homopolymer_run


def _random_bytes(n: int, seed: int) -> bytes:
    rng = random.Random(seed)
    return bytes(rng.getrandbits(8) for _ in range(n))


def test_s2_constraints():
    codec = ConstrainedCodec(chunk_data_bytes=512, gc_target=0.5)
    strands = codec.encode_file(_random_bytes(4096, 7))
    runs = [max_homopolymer_run(s.dna) for s in strands]
    gcs = [gc_fraction(s.dna) for s in strands]
    assert max(runs) <= 1
    assert 0.35 <= sum(gcs) / len(gcs) <= 0.65


def test_s3_constraints():
    codec = RSIndexedCodec(chunk_data_bytes=512, marker_period=40, replication=2)
    strands = codec.encode_file(_random_bytes(4096, 8))
    # Marker insertion may introduce short repeats at boundaries; core constrained coding still dominates.
    runs = [max_homopolymer_run(s.dna) for s in strands]
    gcs = [gc_fraction(s.dna) for s in strands]
    assert max(runs) <= 2
    assert 0.30 <= sum(gcs) / len(gcs) <= 0.70
