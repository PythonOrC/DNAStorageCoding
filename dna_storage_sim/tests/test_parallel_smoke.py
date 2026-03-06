"""Smoke test for parallel run_grid and the new S3 codec fixes."""
from __future__ import annotations

import os
import random
import tempfile

from dna_storage_sim.channel import apply_channel
from dna_storage_sim.codec_base import ObservedStrand
from dna_storage_sim.codec_rs_indexed import RSIndexedCodec
from dna_storage_sim.config import (
    ChannelParams,
    ExperimentConfig,
    GridSpec,
    OutputSpec,
    RunSpec,
    SchemeParams,
    TwoStageChannelParams,
)
from dna_storage_sim.experiments import run_grid
from dna_storage_sim.metrics import reassemble_bytes


def test_s3_recovers_under_substitutions():
    """S3 with segment-reset + RS should recover perfectly at moderate sub rates."""
    codec = RSIndexedCodec(
        chunk_data_bytes=128, rs_parity_bytes=32, marker_period=30,
        max_marker_edit_distance=2, replication=3,
    )
    data = bytes(random.Random(99).getrandbits(8) for _ in range(512))
    encoded = codec.encode_file(data)
    rng = random.Random(123)
    observed = []
    for s in encoded:
        noised = apply_channel(s.dna, ChannelParams(p_sub=0.001, p_del=0, p_ins=0), rng)
        observed.append(ObservedStrand(
            scheme_id=s.scheme_id, chunk_id=s.chunk_id, replica_id=s.replica_id,
            dna=noised, bases_total=s.bases_total, meta=s.meta,
        ))
    decoded = codec.decode_strands(observed)
    recovered = reassemble_bytes(decoded)
    assert recovered == data, f"recovered {len(decoded.chunks)}/{(len(data)+127)//128} chunks"


def test_parallel_run_grid():
    """Parallel (n_workers=2) run_grid completes without error."""
    tmp = os.path.join(tempfile.gettempdir(), "dna_test_parallel")
    rs = RunSpec(
        experiment=ExperimentConfig(
            schemes=("s1", "s3"), dataset="random", size_mb=0.005,
            trials_per_cell=2, base_seed=42, n_workers=2,
        ),
        scheme_params=SchemeParams(
            chunk_data_bytes=128, rs_parity_bytes=16,
            marker_period=30, replication=2,
        ),
        channel=TwoStageChannelParams(
            synthesis=ChannelParams(p_sub=0, p_del=0, p_ins=0),
            sequencing=ChannelParams(p_sub=0, p_del=0, p_ins=0),
            enabled=False,
        ),
        grid=GridSpec(
            p_sub_list=(0.0, 0.001), p_indel_list=(0.0,),
            replication_list=(1, 2),
        ),
        output=OutputSpec(out_dir=tmp, run_id="par_smoke", save_raw_parquet=False),
    )
    out = run_grid(rs)
    assert out.exists()
    assert (out / "agg" / "aggregate_metrics.csv").exists()
