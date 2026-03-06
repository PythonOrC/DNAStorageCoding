from __future__ import annotations

from dna_storage_sim.codec_base import DecodeResult, DecodedChunk
from dna_storage_sim.experiments import _stable_trial_seed
from dna_storage_sim.metrics import compute_trial_metrics


def test_stable_trial_seed_is_deterministic():
    a = _stable_trial_seed(12345, "s1", 0.01, 0.02, 7)
    b = _stable_trial_seed(12345, "s1", 0.01, 0.02, 7)
    c = _stable_trial_seed(12345, "s1", 0.01, 0.02, 8)
    assert a == b
    assert a != c


def test_chunk_aligned_byte_accuracy_handles_missing_early_chunk():
    original = b"ABCDWXYZ"
    decode = DecodeResult(
        chunks={1: DecodedChunk(chunk_id=1, data=b"WXYZ", valid_crc=True)},
        total_chunks_expected=2,
        failures=0,
    )
    m = compute_trial_metrics(
        scheme="s1",
        dataset="random",
        trial=0,
        p_sub=0.0,
        p_ins=0.0,
        p_del=0.0,
        replication=1,
        original=original,
        decode=decode,
        total_bases=100,
        expected_chunks=2,
        chunk_data_bytes=4,
    )
    # One out of two chunks recovered correctly: 4/8 bytes.
    assert m.byte_accuracy == 0.5
