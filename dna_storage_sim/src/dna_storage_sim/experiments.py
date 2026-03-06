from __future__ import annotations

import concurrent.futures
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import platform
import random
import subprocess
import time

import pandas as pd
from tqdm import tqdm

from .channel import apply_channel, apply_two_stage_channel
from .codec_base import EncodedStrand, ObservedStrand
from .codec_constrained import ConstrainedCodec
from .codec_naive import Naive2BitCodec
from .codec_rs_indexed import RSIndexedCodec
from .config import ChannelParams, RunSpec
from .datasets import make_dataset
from .metrics import aggregate_metrics, compute_trial_metrics
from .utils_bits import gc_fraction, max_homopolymer_run

_W_SCHEME: str | None = None
_W_DATASET: bytes | None = None
_W_ENCODED_DICTS: list[dict] | None = None
_W_EXPECTED_CHUNKS: int = 0
_W_RUN_SPEC_DICT: dict | None = None


def _stable_trial_seed(base_seed: int, scheme: str, p_sub: float, p_indel: float, trial: int) -> int:
    # Stable across processes and platforms; avoids Python's randomized hash().
    key = f"{base_seed}|{scheme}|{p_sub:.8f}|{p_indel:.8f}|{trial}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    offset = int.from_bytes(digest[:4], byteorder="big", signed=False)
    return (base_seed + offset) & 0xFFFFFFFF


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
            p = path_no_ext.parent / f"{path_no_ext.name}.parquet"
            df.to_parquet(p, index=False)
            return p
        except Exception:
            pass
    p = path_no_ext.parent / f"{path_no_ext.name}.csv"
    df.to_csv(p, index=False)
    return p


def _count_scheme_cell_files(raw_dir: Path, scheme: str) -> int:
    keys: set[str] = set()
    for p in raw_dir.glob(f"{scheme}_psub_*_pindel_*.csv"):
        keys.add(p.stem)
    for p in raw_dir.glob(f"{scheme}_psub_*_pindel_*.parquet"):
        keys.add(p.stem)
    return len(keys)


def _resolve_n_workers(requested: int, total_cells: int) -> int:
    """Return an efficient worker count for this machine/run."""
    if total_cells <= 1:
        return 1
    logical = os.cpu_count() or 1
    if requested <= 0:
        # Auto mode: keep a small margin for OS/UI responsiveness.
        requested = max(1, logical - 2)
    return max(1, min(requested, logical, total_cells))


def _init_worker_context(
    scheme: str,
    dataset: bytes,
    encoded_dicts: list[dict],
    expected_chunks: int,
    run_spec_dict: dict,
) -> None:
    global _W_SCHEME, _W_DATASET, _W_ENCODED_DICTS, _W_EXPECTED_CHUNKS, _W_RUN_SPEC_DICT
    _W_SCHEME = scheme
    _W_DATASET = dataset
    _W_ENCODED_DICTS = encoded_dicts
    _W_EXPECTED_CHUNKS = expected_chunks
    _W_RUN_SPEC_DICT = run_spec_dict


def _run_cell_trials_impl(
    scheme: str,
    dataset: bytes,
    encoded_dicts: list[dict],
    expected_chunks: int,
    p_sub: float,
    p_indel: float,
    run_spec_dict: dict,
) -> tuple[list[dict], list[dict]]:
    """Run all trials for a single grid cell."""
    run_spec = RunSpec.from_dict(run_spec_dict)
    codec = _codec_for_scheme(scheme, run_spec)
    encoded = [
        EncodedStrand(
            scheme_id=d["scheme_id"],
            chunk_id=d["chunk_id"],
            replica_id=d["replica_id"],
            dna=d["dna"],
            bases_total=d["bases_total"],
            meta=d["meta"],
        )
        for d in encoded_dicts
    ]
    exp = run_spec.experiment
    p_ins = p_indel / 2.0
    p_del = p_indel / 2.0
    synth = ChannelParams(
        p_sub=p_sub,
        p_ins=p_ins,
        p_del=p_del,
        gc_ins_bias=run_spec.channel.synthesis.gc_ins_bias,
        gc_sub_bias=run_spec.channel.synthesis.gc_sub_bias,
        homopolymer_threshold=run_spec.channel.synthesis.homopolymer_threshold,
        homopolymer_del_multiplier=run_spec.channel.synthesis.homopolymer_del_multiplier,
    )
    trial_rows: list[dict] = []
    seed_rows: list[dict] = []
    for trial in range(exp.trials_per_cell):
        trial_seed = _stable_trial_seed(
            base_seed=exp.base_seed, scheme=scheme, p_sub=p_sub, p_indel=p_indel, trial=trial
        )
        rng = random.Random(trial_seed)
        observed: list[ObservedStrand] = []
        total_bases = 0
        for strand in encoded:
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
                    meta={**strand.meta, "p_indel": p_indel},
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
            chunk_data_bytes=run_spec.scheme_params.chunk_data_bytes,
        )
        trial_rows.append(metric.to_dict())
        seed_rows.append(
            {"scheme": scheme, "p_sub": p_sub, "p_indel": p_indel, "trial": trial, "seed": trial_seed}
        )
    return trial_rows, seed_rows


def _run_cell_trials(
    p_sub: float,
    p_indel: float,
) -> tuple[list[dict], list[dict]]:
    """Worker entrypoint; large immutable inputs are loaded once via initializer."""
    if _W_SCHEME is None or _W_DATASET is None or _W_ENCODED_DICTS is None or _W_RUN_SPEC_DICT is None:
        raise RuntimeError("worker context is not initialized")
    return _run_cell_trials_impl(
        scheme=_W_SCHEME,
        dataset=_W_DATASET,
        encoded_dicts=_W_ENCODED_DICTS,
        expected_chunks=_W_EXPECTED_CHUNKS,
        p_sub=p_sub,
        p_indel=p_indel,
        run_spec_dict=_W_RUN_SPEC_DICT,
    )


def run_grid(run_spec: RunSpec) -> Path:
    exp = run_spec.experiment
    out_root = Path(run_spec.output.out_dir) / run_spec.output.run_id
    raw_dir = out_root / "raw"
    agg_dir = out_root / "agg"
    _write_manifest(out_root, run_spec)

    size_bytes = int(exp.size_mb * 1024 * 1024)
    dataset = make_dataset(exp.dataset, size_bytes=size_bytes, seed=exp.base_seed)
    schemes = exp.schemes if exp.schemes != ("all",) else ("s1", "s2", "s3")
    run_spec_dict = run_spec.to_dict()

    trial_rows: list[dict] = []
    seed_rows: list[dict] = []
    total_cells = len(schemes) * len(run_spec.grid.p_sub_list) * len(run_spec.grid.p_indel_list)
    n_workers = _resolve_n_workers(getattr(exp, "n_workers", 1), total_cells=total_cells)
    cell_pbar = tqdm(total=total_cells, desc="grid-cells", position=0)

    for scheme in schemes:
        expected_scheme_cells = len(run_spec.grid.p_sub_list) * len(run_spec.grid.p_indel_list)
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

        encoded_dicts = [asdict(s) for s in encoded]

        # Collect cells that still need to run.
        cells_to_run: list[tuple[float, float]] = []
        for p_sub in run_spec.grid.p_sub_list:
            for p_indel in run_spec.grid.p_indel_list:
                cell_key = f"{scheme}_psub_{p_sub:.6f}_pindel_{p_indel:.6f}"
                if (raw_dir / f"{cell_key}.csv").exists() or (raw_dir / f"{cell_key}.parquet").exists():
                    cell_pbar.update(1)
                    continue
                cells_to_run.append((p_sub, p_indel))

        if not cells_to_run:
            continue

        scheme_workers = _resolve_n_workers(n_workers, total_cells=len(cells_to_run))
        if scheme_workers > 1 and len(cells_to_run) > 1:
            # --- parallel path ---------------------------------------------------
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=scheme_workers,
                initializer=_init_worker_context,
                initargs=(scheme, dataset, encoded_dicts, expected_chunks, run_spec_dict),
            ) as executor:
                future_to_cell = {
                    executor.submit(
                        _run_cell_trials,
                        p_sub, p_indel,
                    ): (p_sub, p_indel)
                    for p_sub, p_indel in cells_to_run
                }
                pending = set(future_to_cell.keys())
                last_heartbeat = time.perf_counter()
                last_done_cell: tuple[float, float] | None = None
                while pending:
                    done, pending = concurrent.futures.wait(
                        pending,
                        timeout=10.0,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    if not done:
                        now = time.perf_counter()
                        if now - last_heartbeat >= 10.0:
                            done_cells = int(cell_pbar.n)
                            rem_cells = int(total_cells - done_cells)
                            if last_done_cell is None:
                                last_done_text = "none"
                            else:
                                last_done_text = (
                                    f"p_sub={last_done_cell[0]:.4f} p_indel={last_done_cell[1]:.4f}"
                                )
                            cell_pbar.write(
                                f"[heartbeat] scheme={scheme} done_cells={done_cells} "
                                f"rem_cells={rem_cells} active_futures={len(pending)} "
                                f"last_done={last_done_text}"
                            )
                            last_heartbeat = now
                        continue
                    for future in done:
                        p_sub, p_indel = future_to_cell[future]
                        cell_key = f"{scheme}_psub_{p_sub:.6f}_pindel_{p_indel:.6f}"
                        cell_trial_rows, cell_seed_rows = future.result()
                        trial_rows.extend(cell_trial_rows)
                        seed_rows.extend(cell_seed_rows)
                        _save_df(
                            pd.DataFrame(cell_trial_rows),
                            raw_dir / cell_key,
                            run_spec.output.save_raw_parquet,
                        )
                        cell_pbar.update(1)
                        cell_pbar.set_postfix_str(f"{scheme} p_sub={p_sub:.4f} p_indel={p_indel:.4f}")
                        last_done_cell = (p_sub, p_indel)
                        last_heartbeat = time.perf_counter()
        else:
            # --- sequential path -------------------------------------------------
            for p_sub, p_indel in cells_to_run:
                cell_key = f"{scheme}_psub_{p_sub:.6f}_pindel_{p_indel:.6f}"
                cell_pbar.set_postfix_str(f"{scheme} p_sub={p_sub:.4f} p_indel={p_indel:.4f}")
                t0 = time.perf_counter()
                trial_desc = f"trials {scheme} p_sub={p_sub:.3f} p_indel={p_indel:.3f}"
                with tqdm(total=exp.trials_per_cell, desc=trial_desc, position=1, leave=False) as trial_pbar:
                    cell_trial_rows, cell_seed_rows = _run_cell_trials_impl(
                        scheme=scheme,
                        dataset=dataset,
                        encoded_dicts=encoded_dicts,
                        expected_chunks=expected_chunks,
                        p_sub=p_sub,
                        p_indel=p_indel,
                        run_spec_dict=run_spec_dict,
                    )
                    for i, row in enumerate(cell_trial_rows, start=1):
                        trial_rows.append(row)
                        seed_rows.append(cell_seed_rows[i - 1])
                        trial_pbar.update(1)
                        elapsed = time.perf_counter() - t0
                        sec_per_trial = elapsed / max(1, i)
                        done = int(cell_pbar.n)
                        rem = int(total_cells - done)
                        trial_pbar.set_postfix_str(
                            f"done_cells={done} rem_cells={rem} sec_per_trial={sec_per_trial:.2f}"
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
                cell_pbar.update(1)
        saved_cells = _count_scheme_cell_files(raw_dir, scheme)
        if saved_cells != expected_scheme_cells:
            cell_pbar.write(
                f"[warning] scheme={scheme} raw_cell_files={saved_cells} "
                f"expected={expected_scheme_cells}. Existing raw files may be incomplete or collided."
            )
    cell_pbar.close()

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
