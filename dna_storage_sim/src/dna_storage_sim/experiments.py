from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import platform
import random
import subprocess

import pandas as pd
from tqdm import tqdm

from .channel import apply_channel, apply_two_stage_channel
from .codec_base import ObservedStrand
from .codec_constrained import ConstrainedCodec
from .codec_naive import Naive2BitCodec
from .codec_rs_indexed import RSIndexedCodec
from .config import ChannelParams, RunSpec
from .datasets import make_dataset
from .metrics import aggregate_metrics, compute_trial_metrics
from .utils_bits import gc_fraction, max_homopolymer_run


def _codec_for_scheme(scheme: str, run_spec: RunSpec):
    p = run_spec.scheme_params
    if scheme == "s1":
        return Naive2BitCodec(chunk_data_bytes=p.chunk_data_bytes)
    if scheme == "s2":
        return ConstrainedCodec(chunk_data_bytes=p.chunk_data_bytes, gc_target=p.gc_target)
    if scheme == "s3":
        return RSIndexedCodec(
            chunk_data_bytes=p.chunk_data_bytes,
            gc_target=p.gc_target,
            rs_parity_bytes=p.rs_parity_bytes,
            marker=p.marker,
            marker_period=p.marker_period,
            max_marker_edit_distance=p.max_marker_edit_distance,
            replication=p.replication,
        )
    raise ValueError(f"unknown scheme {scheme}")


def _safe_git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


def _write_manifest(base: Path, run_spec: RunSpec) -> None:
    cfg = base / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "run_spec.json").write_text(json.dumps(run_spec.to_dict(), indent=2), encoding="utf-8")
    env = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": _safe_git_commit(),
        "pid": os.getpid(),
    }
    (cfg / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")


def _save_df(df: pd.DataFrame, path_no_ext: Path, prefer_parquet: bool) -> Path:
    path_no_ext.parent.mkdir(parents=True, exist_ok=True)
    if prefer_parquet:
        try:
            p = path_no_ext.with_suffix(".parquet")
            df.to_parquet(p, index=False)
            return p
        except Exception:
            pass
    p = path_no_ext.with_suffix(".csv")
    df.to_csv(p, index=False)
    return p


def run_grid(run_spec: RunSpec) -> Path:
    exp = run_spec.experiment
    out_root = Path(run_spec.output.out_dir) / run_spec.output.run_id
    raw_dir = out_root / "raw"
    agg_dir = out_root / "agg"
    _write_manifest(out_root, run_spec)

    size_bytes = exp.size_mb * 1024 * 1024
    dataset = make_dataset(exp.dataset, size_bytes=size_bytes, seed=exp.base_seed)
    schemes = exp.schemes if exp.schemes != ("all",) else ("s1", "s2", "s3")

    trial_rows = []
    seed_rows = []
    total_cells = len(schemes) * len(run_spec.grid.p_sub_list) * len(run_spec.grid.p_indel_list)
    pbar = tqdm(total=total_cells, desc="grid-cells")

    for scheme in schemes:
        codec = _codec_for_scheme(scheme, run_spec)
        encoded = codec.encode_file(dataset)
        expected_chunks = max((s.chunk_id for s in encoded), default=-1) + 1
        gc_vals = [gc_fraction(s.dna) for s in encoded]
        hp_vals = [max_homopolymer_run(s.dna) for s in encoded]
        stat_df = pd.DataFrame(
            {
                "scheme": [scheme],
                "gc_mean": [sum(gc_vals) / max(1, len(gc_vals))],
                "max_homopolymer_mean": [sum(hp_vals) / max(1, len(hp_vals))],
            }
        )
        _save_df(stat_df, agg_dir / f"constraint_stats_{scheme}", run_spec.output.save_raw_parquet)

        for p_sub in run_spec.grid.p_sub_list:
            for p_indel in run_spec.grid.p_indel_list:
                p_ins = p_indel / 2.0
                p_del = p_indel / 2.0
                cell_key = f"{scheme}_psub_{p_sub:.6f}_pindel_{p_indel:.6f}"
                existing_csv = raw_dir / f"{cell_key}.csv"
                existing_parquet = raw_dir / f"{cell_key}.parquet"
                if existing_csv.exists() or existing_parquet.exists():
                    pbar.update(1)
                    continue
                for trial in range(exp.trials_per_cell):
                    trial_seed = exp.base_seed + (hash((scheme, p_sub, p_indel, trial)) & 0xFFFFFFFF)
                    rng = random.Random(trial_seed)
                    observed = []
                    total_bases = 0
                    for strand in encoded:
                        synth = ChannelParams(
                            p_sub=p_sub,
                            p_ins=p_ins,
                            p_del=p_del,
                            gc_ins_bias=run_spec.channel.synthesis.gc_ins_bias,
                            gc_sub_bias=run_spec.channel.synthesis.gc_sub_bias,
                            homopolymer_threshold=run_spec.channel.synthesis.homopolymer_threshold,
                            homopolymer_del_multiplier=run_spec.channel.synthesis.homopolymer_del_multiplier,
                        )
                        if run_spec.channel.enabled:
                            noised = apply_two_stage_channel(
                                strand.dna, synthesis=synth, sequencing=run_spec.channel.sequencing, rng=rng
                            )
                        else:
                            noised = apply_channel(strand.dna, params=synth, rng=rng)
                        total_bases += strand.bases_total
                        observed.append(
                            ObservedStrand(
                                scheme_id=strand.scheme_id,
                                chunk_id=strand.chunk_id,
                                replica_id=strand.replica_id,
                                dna=noised,
                                bases_total=strand.bases_total,
                                meta=strand.meta,
                            )
                        )
                    decoded = codec.decode_strands(observed)
                    metric = compute_trial_metrics(
                        scheme=scheme,
                        dataset=exp.dataset,
                        trial=trial,
                        p_sub=p_sub,
                        p_ins=p_ins,
                        p_del=p_del,
                        replication=run_spec.scheme_params.replication if scheme == "s3" else 1,
                        original=dataset,
                        decode=decoded,
                        total_bases=total_bases,
                        expected_chunks=expected_chunks,
                    )
                    trial_rows.append(metric.to_dict())
                    seed_rows.append(
                        {
                            "scheme": scheme,
                            "p_sub": p_sub,
                            "p_indel": p_indel,
                            "trial": trial,
                            "seed": trial_seed,
                        }
                    )
                cell_df = pd.DataFrame(
                    [
                        r
                        for r in trial_rows
                        if r["scheme"] == scheme
                        and r["p_sub"] == p_sub
                        and abs((r["p_ins"] + r["p_del"]) - p_indel) < 1e-9
                    ]
                )
                _save_df(cell_df, raw_dir / cell_key, run_spec.output.save_raw_parquet)
                pbar.update(1)
    pbar.close()

    if trial_rows:
        all_trials = pd.DataFrame(trial_rows)
    else:
        all_trials = _read_raw_trials(raw_dir)
    _save_df(all_trials, raw_dir / "all_trials", run_spec.output.save_raw_parquet)
    agg = aggregate_metrics(all_trials)
    _save_df(agg, agg_dir / "aggregate_metrics", run_spec.output.save_raw_parquet)
    pd.DataFrame(seed_rows).to_csv(out_root / "config" / "seed_manifest.csv", index=False)
    return out_root


def _read_raw_trials(raw_dir: Path) -> pd.DataFrame:
    frames = []
    for p in raw_dir.glob("*.parquet"):
        if p.name == "all_trials.parquet":
            continue
        try:
            frames.append(pd.read_parquet(p))
        except Exception:
            continue
    for p in raw_dir.glob("*.csv"):
        if p.name == "all_trials.csv":
            continue
        frames.append(pd.read_csv(p))
    if not frames:
        raise RuntimeError(f"no raw trial files found in {raw_dir}")
    return pd.concat(frames, ignore_index=True)
