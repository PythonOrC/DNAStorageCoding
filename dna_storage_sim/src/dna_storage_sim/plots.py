from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _pivot_metric(df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    df = df.copy()
    df["p_indel"] = df["p_ins"] + df["p_del"]
    return df.pivot_table(index="p_sub", columns="p_indel", values=metric_col, aggfunc="mean")


def plot_phase_diagrams(agg_df: pd.DataFrame, out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    produced: list[Path] = []
    for scheme in sorted(agg_df["scheme"].unique()):
        sdf = agg_df[agg_df["scheme"] == scheme]
        piv = _pivot_metric(sdf, "success_mean")
        fig, ax = plt.subplots(figsize=(7, 5))
        im = ax.imshow(piv.values, origin="lower", aspect="auto", vmin=0.0, vmax=1.0, cmap="viridis")
        ax.set_title(f"{scheme.upper()} Success Rate Heatmap")
        ax.set_xlabel("Indel rate (p_ins + p_del)")
        ax.set_ylabel("Substitution rate (p_sub)")
        ax.set_xticks(range(len(piv.columns)))
        ax.set_xticklabels([f"{c:.3f}" for c in piv.columns], rotation=45)
        ax.set_yticks(range(len(piv.index)))
        ax.set_yticklabels([f"{r:.3f}" for r in piv.index])
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("success_rate")
        png = out / f"heatmap_success_{scheme}.png"
        svg = out / f"heatmap_success_{scheme}.svg"
        fig.tight_layout()
        fig.savefig(png, dpi=180)
        fig.savefig(svg)
        plt.close(fig)
        produced.extend([png, svg])

    fig, ax = plt.subplots(figsize=(7, 5))
    for scheme in sorted(agg_df["scheme"].unique()):
        sdf = agg_df[agg_df["scheme"] == scheme].copy()
        sdf["p_indel"] = sdf["p_ins"] + sdf["p_del"]
        line = sdf.groupby("p_indel")["effective_bits_per_base_mean"].mean().sort_index()
        ax.plot(line.index, line.values, marker="o", label=scheme.upper())
    ax.set_title("Effective Bits/Base vs Indel Rate")
    ax.set_xlabel("indel rate")
    ax.set_ylabel("effective bits/base")
    ax.grid(True, alpha=0.25)
    ax.legend()
    png = out / "line_effective_bits_vs_indel.png"
    svg = out / "line_effective_bits_vs_indel.svg"
    fig.tight_layout()
    fig.savefig(png, dpi=180)
    fig.savefig(svg)
    plt.close(fig)
    produced.extend([png, svg])
    return produced
