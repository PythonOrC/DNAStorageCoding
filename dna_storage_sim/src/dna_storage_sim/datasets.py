from __future__ import annotations

import random


LOREM = (
    "DNA data storage explores encoding digital bytes into nucleotide sequences. "
    "This synthetic corpus repeats mixed-length sentences to model text-like redundancy. "
)


def make_dataset(kind: str, size_bytes: int, seed: int) -> bytes:
    rng = random.Random(seed)
    if kind == "random":
        return bytes(rng.getrandbits(8) for _ in range(size_bytes))
    if kind == "text":
        text = []
        while len("".join(text).encode("utf-8")) < size_bytes:
            sentence = LOREM + f"seed={seed} token={rng.randint(0, 1_000_000)}. "
            text.append(sentence)
        return "".join(text).encode("utf-8")[:size_bytes]
    raise ValueError(f"unsupported dataset kind: {kind}")
