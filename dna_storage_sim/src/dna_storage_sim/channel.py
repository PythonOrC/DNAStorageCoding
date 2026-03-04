from __future__ import annotations

from dataclasses import dataclass
import random

from .config import ChannelParams

BASES = ("A", "C", "G", "T")


def _sample_base(gc_bias: float, rng: random.Random, exclude: str | None = None) -> str:
    choices = [b for b in BASES if b != exclude]
    weights = []
    for b in choices:
        if b in ("G", "C"):
            w = max(1e-6, 1.0 + gc_bias)
        else:
            w = max(1e-6, 1.0 - gc_bias)
        weights.append(w)
    total = sum(weights)
    x = rng.random() * total
    csum = 0.0
    for b, w in zip(choices, weights):
        csum += w
        if x <= csum:
            return b
    return choices[-1]


def apply_channel(dna: str, params: ChannelParams, rng: random.Random) -> str:
    out: list[str] = []
    run_len = 1
    prev_in = ""
    for base in dna:
        if prev_in == base:
            run_len += 1
        else:
            run_len = 1
        prev_in = base

        p_del_eff = params.p_del
        if run_len >= params.homopolymer_threshold:
            p_del_eff *= params.homopolymer_del_multiplier
        if rng.random() < min(1.0, p_del_eff):
            continue

        emitted = base
        if rng.random() < params.p_sub:
            emitted = _sample_base(params.gc_sub_bias, rng, exclude=base)
        out.append(emitted)

        if rng.random() < params.p_ins:
            out.append(_sample_base(params.gc_ins_bias, rng, exclude=None))
    return "".join(out)


def apply_two_stage_channel(
    dna: str, synthesis: ChannelParams, sequencing: ChannelParams, rng: random.Random
) -> str:
    tmp = apply_channel(dna, synthesis, rng)
    return apply_channel(tmp, sequencing, rng)
