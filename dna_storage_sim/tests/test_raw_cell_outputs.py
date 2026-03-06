from __future__ import annotations

from pathlib import Path

import pandas as pd

from dna_storage_sim.experiments import _count_scheme_cell_files, _save_df


def test_save_df_preserves_fractional_cell_key_in_filename(monkeypatch):
    written: dict[str, Path] = {}

    def fake_mkdir(self, parents=False, exist_ok=False):
        return None

    def fake_to_csv(self, path, index=False):
        written["path"] = Path(path)
        written["index"] = index

    monkeypatch.setattr(Path, "mkdir", fake_mkdir, raising=True)
    monkeypatch.setattr(pd.DataFrame, "to_csv", fake_to_csv, raising=True)

    df = pd.DataFrame({"x": [1]})
    stem = Path("results/final/raw/s1_psub_0.000200_pindel_0.000100")
    out = _save_df(df, stem, prefer_parquet=False)

    assert out == Path("results/final/raw/s1_psub_0.000200_pindel_0.000100.csv")
    assert written["path"] == out
    assert written["index"] is False


def test_count_scheme_cell_files_deduplicates_extensions(monkeypatch):
    def fake_glob(self, pattern):
        if pattern.endswith(".csv"):
            return [
                Path("s1_psub_0.000200_pindel_0.000100.csv"),
                Path("s1_psub_0.000200_pindel_0.000200.csv"),
            ]
        if pattern.endswith(".parquet"):
            return [
                Path("s1_psub_0.000200_pindel_0.000100.parquet"),
            ]
        return []

    monkeypatch.setattr(Path, "glob", fake_glob, raising=True)
    assert _count_scheme_cell_files(Path("unused"), "s1") == 2
