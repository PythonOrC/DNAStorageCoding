from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class EncodedStrand:
    scheme_id: str
    chunk_id: int
    replica_id: int
    dna: str
    bases_total: int
    meta: dict = field(default_factory=dict)


@dataclass
class ObservedStrand:
    scheme_id: str
    chunk_id: int
    replica_id: int
    dna: str
    bases_total: int
    meta: dict = field(default_factory=dict)


@dataclass
class DecodedChunk:
    chunk_id: int
    data: bytes
    valid_crc: bool
    meta: dict = field(default_factory=dict)


@dataclass
class DecodeResult:
    chunks: dict[int, DecodedChunk]
    total_chunks_expected: int
    failures: int = 0


class Codec(ABC):
    scheme_id: str

    @abstractmethod
    def encode_file(self, data: bytes) -> list[EncodedStrand]:
        raise NotImplementedError

    @abstractmethod
    def decode_strands(self, strands: list[ObservedStrand]) -> DecodeResult:
        raise NotImplementedError
