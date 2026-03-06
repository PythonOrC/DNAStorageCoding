from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _pivot_metric(df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    df = df.copy()
    df["p_indel"] = df["p_ins"] + df["p_del"]
    return df.pivot_table(index="p_sub", columns="p_indel", values=metric_col, aggfunc="mean")


def _chunk_recovery_frontier(df: pd.DataFrame, threshold: float = 0.0) -> pd.DataFrame:
    work = df.copy()
    work["p_indel"] = work["p_ins"] + work["p_del"]
    nz = work[work["chunk_recovery_mean"] > threshold]
    if nz.empty:
        return pd.DataFrame(columns=["scheme", "p_sub", "max_nonzero_p_indel"])
    frontier = (
        nz.groupby(["scheme", "p_sub"], as_index=False)["p_indel"]
        .max()
        .rename(columns={"p_indel": "max_nonzero_p_indel"})
        .sort_values(["scheme", "p_sub"])
    )
    return frontier


def plot_phase_diagrams(agg_df: pd.DataFrame, out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    produced: list[Path] = []
    for scheme in sorted(agg_df["scheme"].unique()):
        sdf = agg_df[agg_df["scheme"] == scheme]
        for metric_col, title, stem in [
            ("success_mean", "Success Rate", "success"),
            ("chunk_recovery_mean", "Chunk Recovery", "chunk_recovery"),
            ("byte_accuracy_mean", "Byte Accuracy", "byte_accuracy"),
        ]:
            piv = _pivot_metric(sdf, metric_col)
            fig, ax = plt.subplots(figsize=(7, 5))
            im = ax.imshow(piv.values, origin="lower", aspect="auto", vmin=0.0, vmax=1.0, cmap="viridis")
            ax.set_title(f"{scheme.upper()} {title} Heatmap")
            ax.set_xlabel("Indel rate (p_ins + p_del)")
            ax.set_ylabel("Substitution rate (p_sub)")
            ax.set_xticks(range(len(piv.columns)))
            ax.set_xticklabels([f"{c:.3f}" for c in piv.columns], rotation=45)
            ax.set_yticks(range(len(piv.index)))
            ax.set_yticklabels([f"{r:.3f}" for r in piv.index])
            cbar = fig.colorbar(im, ax=ax)
            cbar.set_label(metric_col)
            png = out / f"heatmap_{stem}_{scheme}.png"
            svg = out / f"heatmap_{stem}_{scheme}.svg"
            fig.tight_layout()
            fig.savefig(png, dpi=180)
            fig.savefig(svg)
            plt.close(fig)
            produced.extend([png, svg])

    for metric_col, title, y_label, stem in [
        ("effective_bits_per_base_mean", "Effective Bits/Base vs Indel Rate", "effective bits/base", "effective_bits"),
        ("chunk_recovery_mean", "Chunk Recovery vs Indel Rate", "chunk recovery", "chunk_recovery"),
        ("byte_accuracy_mean", "Byte Accuracy vs Indel Rate", "byte accuracy", "byte_accuracy"),
    ]:
        fig, ax = plt.subplots(figsize=(7, 5))
        for scheme in sorted(agg_df["scheme"].unique()):
            sdf = agg_df[agg_df["scheme"] == scheme].copy()
            sdf["p_indel"] = sdf["p_ins"] + sdf["p_del"]
            line = sdf.groupby("p_indel")[metric_col].mean().sort_index()
            ax.plot(line.index, line.values, marker="o", label=scheme.upper())
        ax.set_title(title)
        ax.set_xlabel("indel rate")
        ax.set_ylabel(y_label)
        ax.grid(True, alpha=0.25)
        ax.legend()
        png = out / f"line_{stem}_vs_indel.png"
        svg = out / f"line_{stem}_vs_indel.svg"
        fig.tight_layout()
        fig.savefig(png, dpi=180)
        fig.savefig(svg)
        plt.close(fig)
        produced.extend([png, svg])

    frontier = _chunk_recovery_frontier(agg_df, threshold=0.0)
    if not frontier.empty:
        fig, ax = plt.subplots(figsize=(7, 5))
        for scheme in sorted(frontier["scheme"].unique()):
            sdf = frontier[frontier["scheme"] == scheme].sort_values("p_sub")
            ax.plot(sdf["p_sub"], sdf["max_nonzero_p_indel"], marker="o", label=scheme.upper())
        ax.set_title("Last Nonzero Chunk Recovery Frontier")
        ax.set_xlabel("substitution rate (p_sub)")
        ax.set_ylabel("max indel rate with chunk_recovery > 0")
        ax.grid(True, alpha=0.25)
        ax.legend()
        png = out / "line_chunk_recovery_nonzero_frontier_vs_psub.png"
        svg = out / "line_chunk_recovery_nonzero_frontier_vs_psub.svg"
        fig.tight_layout()
        fig.savefig(png, dpi=180)
        fig.savefig(svg)
        plt.close(fig)
        produced.extend([png, svg])
    return produced
