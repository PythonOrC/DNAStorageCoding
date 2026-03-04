GOAL
Build a reproducible Python simulation to compare 3 DNA-storage encoding schemes under realistic error channels
(substitutions + insertions + deletions + GC bias + homopolymer-sensitive errors).
Produce metrics: recovery success rate, effective bits/base, overhead, and phase-diagram plots vs error rates.

SCHEMES (3)
S1) Naive-2bit:
  - Encode bytes -> bitstring -> base-4 digits -> DNA bases with fixed mapping (00:A, 01:C, 10:G, 11:T)
  - Chunking + indexing for reassembly (chunk_id header) + CRC32 for correctness check.
  - No constraints; no FEC.

S2) Constrained (GC + homopolymer limits):
  - Use a deterministic “constrained coder” that avoids homopolymers and keeps GC near a target.
  - Recommend: ternary coding (Goldman-style) to guarantee no repeated base:
      * Convert bits -> trits (base-3 digits), then map each trit to one of the 3 bases != previous base.
      * Add GC balancing by switching among 2 deterministic mapping tables depending on running GC deviation.
  - Still chunk + index + CRC32, but no RS FEC.

S3) RS-Indexed (Chunking + addressing + Reed–Solomon + sync markers):
  - For each chunk:
      * header: magic + version + chunk_id + total_chunks + payload_len + (optional) header CRC
      * body: data bytes
      * FEC: Reed–Solomon over bytes (e.g., RS(n=255,k=223) style but choose smaller n,k for simplicity).
      * CRC32 over original chunk data (stored in header or footer).
  - Encode bytes -> DNA using the SAME constrained coder as S2 (so RS focuses on correcting substitutions/erasures).
  - Add periodic synchronization markers in DNA to reduce indel desync:
      * Insert a short known marker every M encoded bases (e.g., every 30–50 bases).
      * Decoder uses approximate matching to locate markers and segment the read.
      * If a segment length mismatches expected length due to indels, mark that segment as “erased” (unknown),
        and try RS decode (RS can handle erasures up to parity budget if implemented; otherwise treat as failure).
  - Optional “moderate redundancy”: replicate each chunk R times (R=1..3) and accept first valid decode.

DATASETS
Generate synthetic input files:
  - text: repeated paragraphs / random ASCII text
  - random: high-entropy bytes via RNG
Sizes: parameterized (default 1MB for dev; support 1–10MB).
Each experiment setting runs N trials (default 100; configurable up to 1000).

ERROR MODEL (DNA CHANNEL)
Implement an error channel applied to each synthesized DNA strand:
Parameters (all configurable):
  - p_sub: substitution probability per base
  - p_del: deletion probability per base
  - p_ins: insertion probability per base
  - GC bias: base-dependent substitution/ins probabilities or sampling bias for inserted bases
  - Homopolymer penalty: if current run length >= H (e.g., 4), multiply p_del by factor (e.g., x3–x10)
Two-stage model (optional but clean):
  - synthesis stage: low error (e.g., total ~1%) mostly substitutions + some deletions
  - sequencing stage (nanopore-like): higher error (5–10%) indel-heavy

DECODING + REASSEMBLY
All schemes:
  - Attempt to decode each strand -> bytes
  - Parse header -> chunk_id
  - Validate CRC32 (or RS+CRC)
  - Reassemble chunks in order; final success if all chunks recovered and overall file hash matches (SHA256)
  - Report partial recovery % too (fraction of chunks/bytes recovered)

METRICS
For each scheme and parameter setting:
  - success_rate: fraction of trials with perfect file recovery
  - byte_accuracy: average fraction of bytes correct (0..1)
  - chunk_recovery: fraction of chunks recovered
  - effective_bits_per_base:
        (original_bits_recovered) / (total_bases_synthesized_including_overhead)
    total bases includes: headers + CRC + parity bytes + sync markers + replication factor.
  - overhead:
        (total_bases_synthesized) / (bases_needed_for_raw_payload_at_2bits_per_base)
  - constraint stats (for S2/S3): GC distribution and max homopolymer length distribution

EXPERIMENT GRID (“PHASE DIAGRAM”)
Run sweeps to produce heatmaps:
  - x-axis: indel rate = p_ins + p_del (e.g., 0% to 5%)
  - y-axis: substitution rate p_sub (e.g., 0% to 5%) OR redundancy R (1..3)
For each cell: plot success_rate; one heatmap per scheme.
Also plot effective_bits/base contours or separate plot of effective_bits/base vs indel rate.

IMPLEMENTATION DETAILS
Language: Python 3.10+
Dependencies:
  - numpy, pandas, matplotlib, tqdm
  - reedsolo (for RS coding over bytes)
  - rapidfuzz or python-Levenshtein (optional) for approximate marker finding
  - pytest (tests)

FILE STRUCTURE
dna_storage_sim/
  README.md (how to run)
  requirements.txt
  pyproject.toml (optional)
  src/
    config.py                # dataclasses for experiment config
    utils_bits.py            # bits<->bytes, bits<->trits, CRC32, SHA256
    codec_naive.py           # S1 encode/decode
    codec_constrained.py     # S2 constrained coder (ternary + GC balancing)
    codec_rs_indexed.py      # S3 RS + markers + replication
    channel.py               # error channel implementation
    metrics.py               # compute metrics per trial and aggregate
    experiments.py           # grid runner + result caching
    plots.py                 # phase diagrams + curves
    cli.py                   # command line entrypoint
  tests/
    test_roundtrip.py        # encode->channel(no error)->decode must match
    test_channel_stats.py    # sanity check error rates approx
    test_constraints.py      # max homopolymer, GC bounds (for S2/S3)

CONCRETE ALGORITHMS

A) Chunking format (all schemes)
Choose constants:
  - CHUNK_DATA_BYTES = 1024 (or 2048)  [configurable]
  - HEADER:
      magic(4) = b'DNAS'
      version(1)
      scheme_id(1)
      chunk_id(4)
      total_chunks(4)
      data_len(2)
      crc32_data(4)
    Total header ~20 bytes
  - Payload: data_len bytes
  - For S3: add RS parity bytes after payload (see below)

B) Naive base-4 coder (S1)
encode_bytes_to_dna_naive(b):
  bits = bytes_to_bits(b)
  pad bits to multiple of 2
  for each 2-bit symbol -> base via mapping
decode_dna_to_bytes_naive(dna, expected_bytes):
  map bases -> 2-bit symbols (invalid -> fail)
  truncate/pad to expected length in bits
  bits->bytes

C) Constrained coder (S2)
Goal: avoid homopolymers and keep GC near target.
Steps:
  1) Convert bytes -> bits -> trits:
      - Implement bits_to_trits by interpreting bitstring as integer and converting to base-3,
        OR by streaming conversion (preferred for memory).
      - Keep exact reversibility (store bit-length in header).
  2) Map trits -> bases with a state machine:
      - prev base p in {A,C,G,T}, choose next base from the 3 bases != p.
      - Use two deterministic ordering tables ORDER0[p] and ORDER1[p] (each is a length-3 list).
      - Maintain running GC_count and position i; if GC_count is below target trajectory, pick ORDER1
        else ORDER0. The chosen order table selects which base corresponds to trit 0/1/2.
      - This keeps mapping bijective because decoder can recompute which ORDER was used from already-decoded prefix.
  3) Decoder:
      - Recompute ORDER choice using same GC trajectory rule, recover trits, then trits->bits->bytes.

D) RS + markers (S3)
RS layer:
  - Choose RS parameters over bytes: RS(k=chunk_bytes, parity=p) using reedsolo.RSCodec(parity).
  - Encode: rs = RSCodec(parity); codeword = rs.encode(payload_bytes)  # payload+parity
  - Decode: rs.decode(codeword) -> payload; if fails -> invalid chunk
Markers:
  - Define a marker string unlikely under constraints, e.g., "ACGTACGT" (or longer) but ensure it doesn’t violate your constrained coder;
    if it violates, use a marker built from allowed transitions (e.g., "ACGTCAGT...").
  - Insert marker every M bases in the encoded DNA (not counted as data).
  - Decoder:
      * Find marker positions via exact match; if not found, fall back to approximate match (edit distance <= 1–2).
      * Split into segments between markers; each segment corresponds to a fixed number of trits/bits.
      * If a segment is wrong length or decoding fails, mark chunk invalid (or mark erasures if you implement erasure-aware RS).
Replication:
  - For redundancy R, generate R independently encoded strands per chunk (different seed in header; or different marker phase).
  - On decode, accept the first strand that passes RS+CRC.

E) Error channel (channel.py)
apply_channel(dna, params, rng):
  output = []
  run_len = 1
  for each base in dna:
    # deletion
    p_del_eff = params.p_del * (params.hpoly_del_mult if run_len>=H else 1.0)
    if rng.random() < p_del_eff: 
        continue
    # substitution
    b = base
    if rng.random() < params.p_sub:
        b = random choice among other 3 bases with optional GC bias
    output.append(b)
    # insertion (can happen after emitting base)
    if rng.random() < params.p_ins:
        ins_base = biased_random_base(...)
        output.append(ins_base)
    update run_len based on b vs prev emitted base
Return ''.join(output)

F) Trial runner
run_one_trial(scheme, data_bytes, channel_params, config, rng):
  encode -> list[strands]
  for each strand: apply synthesis channel then sequencing channel
  decode strands -> recovered chunks
  reassemble -> recovered file
  compute metrics (success, bytes_correct, bases_total, effective_rate)

G) Aggregation + plots
For each grid cell:
  - run N trials with fixed seed schedule
  - save per-trial metrics to CSV/Parquet
  - aggregate means + confidence intervals
  - generate plots:
      * heatmap success_rate for each scheme
      * line plots: effective_bits/base vs indel_rate at fixed p_sub
      * optionally: overhead vs success tradeoff

CLI COMMANDS
python -m dna_storage_sim.cli run-grid --scheme all --dataset random --size_mb 1 --trials 200 \
  --p_sub_list 0,0.01,0.02,0.03 --p_indel_list 0,0.005,0.01,0.02 \
  --out results/

python -m dna_storage_sim.cli plot --in results/ --out figs/

ACCEPTANCE TESTS (must pass)
1) Roundtrip with zero noise:
   - For each scheme: encode->decode returns exact original bytes for multiple random seeds and file sizes.
2) Constraint test (S2/S3):
   - max homopolymer length <= configured bound (or exactly guaranteed by ternary rule),
   - GC fraction stays within a reasonable band for typical strand length (report distribution).
3) Channel sanity:
   - empirically measured substitution/ins/del rates approximately match parameters over long sequences.

NOTES/SCOPING
- Keep everything parameterized (strand length, chunk size, marker period, RS parity, redundancy R).
- Default settings should run quickly on CPU; larger sizes/trials should just work by changing CLI args.
- Save all configs + RNG seeds with results for reproducibility.