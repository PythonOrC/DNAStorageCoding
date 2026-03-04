from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import pandas as pd

from .codec_base import DecodeResult
from .utils_bits import sha256_hex


@dataclass
class TrialMetrics:
    scheme: str
    dataset: str
    size_bytes: int
    trial: int
    p_sub: float
    p_ins: float
    p_del: float
    replication: int
    success: int
    byte_accuracy: float
    chunk_recovery: float
    recovered_bytes: int
    expected_chunks: int
    recovered_chunks: int
    total_bases: int
    effective_bits_per_base: float
    overhead: float
    input_sha256: str
    output_sha256: str
    failures: int

    def to_dict(self) -> dict:
        return asdict(self)


def reassemble_bytes(decode: DecodeResult) -> bytes:
    if not decode.chunks:
        return b""
    ordered = [decode.chunks[i].data for i in sorted(decode.chunks)]
    return b"".join(ordered)


def _byte_accuracy(original: bytes, recovered: bytes) -> float:
    if not original:
        return 1.0
    n = min(len(original), len(recovered))
    correct = 0
    for i in range(n):
        if original[i] == recovered[i]:
            correct += 1
    return correct / len(original)


def compute_trial_metrics(
    scheme: str,
    dataset: str,
    trial: int,
    p_sub: float,
    p_ins: float,
    p_del: float,
    replication: int,
    original: bytes,
    decode: DecodeResult,
    total_bases: int,
    expected_chunks: int,
) -> TrialMetrics:
    recovered = reassemble_bytes(decode)
    success = int(sha256_hex(original) == sha256_hex(recovered))
    recovered_chunks = len(decode.chunks)
    chunk_recovery = (recovered_chunks / expected_chunks) if expected_chunks else 0.0
    bits_recovered = 8 * len(recovered)
    effective = bits_recovered / max(1, total_bases)
    raw_payload_2bit = max(1, math.ceil(len(original) * 8 / 2))
    overhead = total_bases / raw_payload_2bit
    return TrialMetrics(
        scheme=scheme,
        dataset=dataset,
        size_bytes=len(original),
        trial=trial,
        p_sub=p_sub,
        p_ins=p_ins,
        p_del=p_del,
        replication=replication,
        success=success,
        byte_accuracy=_byte_accuracy(original, recovered),
        chunk_recovery=chunk_recovery,
        recovered_bytes=len(recovered),
        expected_chunks=expected_chunks,
        recovered_chunks=recovered_chunks,
        total_bases=total_bases,
        effective_bits_per_base=effective,
        overhead=overhead,
        input_sha256=sha256_hex(original),
        output_sha256=sha256_hex(recovered),
        failures=decode.failures,
    )


def aggregate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["scheme", "dataset", "size_bytes", "p_sub", "p_ins", "p_del", "replication"]
    rows = []
    for keys, grp in df.groupby(group_cols):
        row = {k: v for k, v in zip(group_cols, keys)}
        for metric in ["success", "byte_accuracy", "chunk_recovery", "effective_bits_per_base", "overhead"]:
            mean = float(grp[metric].mean())
            std = float(grp[metric].std(ddof=1) if len(grp) > 1 else 0.0)
            ci95 = 1.96 * std / math.sqrt(max(1, len(grp)))
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95"] = ci95
        row["trials"] = int(len(grp))
        rows.append(row)
    return pd.DataFrame(rows)
