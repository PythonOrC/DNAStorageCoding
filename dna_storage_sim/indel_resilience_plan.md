# Indel-Resilient S3 Plan

## Goal
Improve S3 accuracy specifically when `p_indel > 0` by limiting error propagation before RS decoding.

## Benefit vs Error Regime
| Change | Low indel (`<=1e-4`) | Moderate indel (`1e-4..1e-3`) | Higher indel (`>=1e-3`) | Cost/Tradeoff |
|---|---|---|---|---|
| Segment-length validation + segment erasure tagging | Small gain | Strong gain | Strong gain (until RS saturation) | Minimal runtime overhead |
| Fuzzy-marker boundary -> uncertain segment erasure | Small gain | Strong gain | Strong gain | Slightly more erasures in ambiguous cases |
| Exact-path length mismatch -> uncertain segment erasure | Small gain | Medium/strong gain | Medium gain | Conservative (may erase salvageable bytes) |
| Byte-level voting fallback across replicas (already present) | Medium gain | Medium gain | Medium gain | Extra decode work |
| Lower `marker_period` (config tuning) | Small | Medium | Strong | Higher synthesis overhead |
| Larger RS parity (config tuning) | Small | Medium | Strong | Lower effective bits/base |

## Implemented Now
1. Added segment-length mismatch handling in S3 marker segmentation.
   - Non-terminal segments whose observed length differs from expected segment period are marked uncertain.
   - Uncertain segments are treated as erasure regions by resilient constrained decoding.
2. Added the same mismatch marking in both paths:
   - exact marker-strip path
   - fuzzy marker-strip path
3. Wired exact-path uncertain segments into `_decode_to_codeword` so erasures reach RS decode.
4. Added tests for:
   - wrong-length segment detection as uncertain
   - erasure emission in `_decode_to_codeword` after a segment shift

## Why This Helps
With indels, length drift localizes to segment boundaries around markers. Marking those segments as erasures prevents large decode cascades and gives RS a tractable error model (erasures instead of widespread wrong bytes).

## Next Tuning Steps (Config-Only)
1. For indel-heavy runs, use smaller `marker_period` (e.g. 12–18).
2. Increase `rs_parity_bytes` if frontier still drops early.
3. Keep replication at `3`+ when throughput budget allows.

## Validation Checklist
1. Run `pytest -q tests/test_roundtrip.py`.
2. Rerun your indel grid config (`config_s3_fixed_test.json`).
3. Compare:
   - `chunk_recovery_mean` vs `p_sub/p_indel`
   - `line_chunk_recovery_nonzero_frontier_vs_psub.png`
