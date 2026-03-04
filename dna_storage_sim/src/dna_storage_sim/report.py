from __future__ import annotations

from pathlib import Path
import json

import pandas as pd


def _find_file(base: Path, stem: str) -> Path:
    for ext in (".parquet", ".csv"):
        p = base / f"{stem}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"missing file for stem: {stem}")


def _read_df(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _table_to_markdown(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = []
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        vals = [str(row[c]) for c in cols]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def generate_report(result_dir: str | Path, out_md: str | Path) -> Path:
    base = Path(result_dir)
    agg_path = _find_file(base / "agg", "aggregate_metrics")
    agg = _read_df(agg_path)
    top = agg.sort_values(["scheme", "success_mean"], ascending=[True, False]).groupby("scheme").head(5)
    top_table = top[
        [
            "scheme",
            "p_sub",
            "p_ins",
            "p_del",
            "success_mean",
            "effective_bits_per_base_mean",
            "overhead_mean",
            "trials",
        ]
    ].copy()
    table_path = base / "agg" / "summary_top_configs.csv"
    top_table.to_csv(table_path, index=False)
    cfg_path = base / "config" / "run_spec.json"
    cfg_text = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else "{}"
    cfg = json.loads(cfg_text)

    md = f"""# DNA Storage Simulation Report

## Overview
This report summarizes a reproducible run for DNA storage coding schemes S1/S2/S3.

## Run Configuration
```json
{json.dumps(cfg, indent=2)}
```

## Key Results
Top-performing settings per scheme are exported to:
- `{table_path.as_posix()}`

### Top Config Table
{_table_to_markdown(top_table)}

## Figures
- `figs/heatmap_success_s1.png`
- `figs/heatmap_success_s2.png`
- `figs/heatmap_success_s3.png`
- `figs/line_effective_bits_vs_indel.png`

## Interpretation Notes
- `success_mean` captures perfect file recovery probability.
- `effective_bits_per_base_mean` measures net recovered payload rate including overhead.
- `overhead_mean` compares synthesized bases to ideal 2-bit/base payload requirement.
"""
    out_path = Path(out_md)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return out_path
