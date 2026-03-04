from __future__ import annotations

import random

from dna_storage_sim.channel import apply_channel
from dna_storage_sim.config import ChannelParams


def test_channel_sanity_rates():
    dna = "ACGT" * 20000
    params = ChannelParams(
        p_sub=0.02,
        p_del=0.01,
        p_ins=0.01,
        homopolymer_threshold=4,
        homopolymer_del_multiplier=3.0,
    )
    out = apply_channel(dna, params=params, rng=random.Random(123))
    length_ratio = len(out) / len(dna)
    assert 0.90 <= length_ratio <= 1.10


def test_homopolymer_penalty_increases_deletions():
    dna = "AAAAA" * 10000
    base = ChannelParams(
        p_sub=0.0,
        p_del=0.02,
        p_ins=0.0,
        homopolymer_threshold=99,
        homopolymer_del_multiplier=1.0,
    )
    penalized = ChannelParams(
        p_sub=0.0,
        p_del=0.02,
        p_ins=0.0,
        homopolymer_threshold=4,
        homopolymer_del_multiplier=5.0,
    )
    out_base = apply_channel(dna, params=base, rng=random.Random(1))
    out_pen = apply_channel(dna, params=penalized, rng=random.Random(1))
    assert len(out_pen) < len(out_base)
