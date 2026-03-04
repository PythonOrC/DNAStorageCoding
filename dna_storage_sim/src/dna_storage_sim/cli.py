from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .config import RunSpec, default_run_spec
from .experiments import run_grid
from .plots import plot_phase_diagrams
from .report import generate_report


def _read_df_by_stem(base: Path, stem: str) -> pd.DataFrame:
    for ext in (".parquet", ".csv"):
        p = base / f"{stem}{ext}"
        if p.exists():
            if p.suffix == ".parquet":
                return pd.read_parquet(p)
            return pd.read_csv(p)
    raise FileNotFoundError(f"missing {stem}.parquet/.csv in {base}")


def cmd_run_grid(args: argparse.Namespace) -> None:
    run_spec = default_run_spec()
    if args.config:
        run_spec = RunSpec.load_json(args.config)
    exp = run_spec.experiment
    out = run_spec.output
    if args.scheme:
        schemes = ("s1", "s2", "s3") if args.scheme == "all" else tuple(args.scheme.split(","))
        exp = exp.__class__(**{**exp.__dict__, "schemes": schemes})
    if args.dataset:
        exp = exp.__class__(**{**exp.__dict__, "dataset": args.dataset})
    if args.size_mb is not None:
        exp = exp.__class__(**{**exp.__dict__, "size_mb": args.size_mb})
    if args.trials is not None:
        exp = exp.__class__(**{**exp.__dict__, "trials_per_cell": args.trials})
    if args.out:
        out = out.__class__(**{**out.__dict__, "out_dir": args.out})
    if args.run_id is not None:
        out = out.__class__(**{**out.__dict__, "run_id": args.run_id})
    run_spec = RunSpec(
        experiment=exp,
        scheme_params=run_spec.scheme_params,
        channel=run_spec.channel,
        grid=run_spec.grid,
        output=out,
    )
    result = run_grid(run_spec)
    print(f"run complete: {result}")


def cmd_plot(args: argparse.Namespace) -> None:
    in_dir = Path(args.input)
    agg = _read_df_by_stem(in_dir / "agg", "aggregate_metrics")
    out_dir = Path(args.out) if args.out else in_dir / "figs"
    produced = plot_phase_diagrams(agg, out_dir=out_dir)
    for p in produced:
        print(p)


def cmd_report(args: argparse.Namespace) -> None:
    result_dir = Path(args.input)
    out = Path(args.out) if args.out else result_dir / "report.md"
    p = generate_report(result_dir, out)
    print(p)


def cmd_validate_repro(args: argparse.Namespace) -> None:
    result_dir = Path(args.input)
    cfg_path = result_dir / "config" / "run_spec.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"missing {cfg_path}")
    run_spec = RunSpec.load_json(cfg_path)
    rerun_id = f"{run_spec.output.run_id}_repro"
    rerun_spec = RunSpec(
        experiment=run_spec.experiment,
        scheme_params=run_spec.scheme_params,
        channel=run_spec.channel,
        grid=run_spec.grid,
        output=run_spec.output.__class__(**{**run_spec.output.__dict__, "run_id": rerun_id}),
    )
    rerun_dir = run_grid(rerun_spec)
    a = _read_df_by_stem(result_dir / "agg", "aggregate_metrics").sort_values(
        ["scheme", "p_sub", "p_ins", "p_del"]
    )
    b = _read_df_by_stem(rerun_dir / "agg", "aggregate_metrics").sort_values(
        ["scheme", "p_sub", "p_ins", "p_del"]
    )
    cols = ["success_mean", "byte_accuracy_mean", "chunk_recovery_mean", "effective_bits_per_base_mean", "overhead_mean"]
    merged = a.merge(b, on=["scheme", "dataset", "size_bytes", "p_sub", "p_ins", "p_del", "replication"], suffixes=("_a", "_b"))
    diffs = {}
    for c in cols:
        diffs[c] = float((merged[f"{c}_a"] - merged[f"{c}_b"]).abs().max())
    print("repro_diffs_max:", diffs)
    print(f"rerun_dir: {rerun_dir}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DNA storage simulation CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run-grid", help="run experiment grid")
    run.add_argument("--config", type=str, default=None)
    run.add_argument("--scheme", type=str, default="all")
    run.add_argument("--dataset", type=str, default=None, choices=["text", "random"])
    run.add_argument("--size-mb", type=int, default=None)
    run.add_argument("--trials", type=int, default=None)
    run.add_argument("--out", type=str, default=None)
    run.add_argument("--run-id", type=str, default=None)
    run.set_defaults(func=cmd_run_grid)

    plot = sub.add_parser("plot", help="generate figures")
    plot.add_argument("--in", dest="input", required=True, type=str)
    plot.add_argument("--out", type=str, default=None)
    plot.set_defaults(func=cmd_plot)

    rep = sub.add_parser("report", help="generate markdown report")
    rep.add_argument("--in", dest="input", required=True, type=str)
    rep.add_argument("--out", type=str, default=None)
    rep.set_defaults(func=cmd_report)

    vr = sub.add_parser("validate-repro", help="rerun and compare aggregates")
    vr.add_argument("--in", dest="input", required=True, type=str)
    vr.set_defaults(func=cmd_validate_repro)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
