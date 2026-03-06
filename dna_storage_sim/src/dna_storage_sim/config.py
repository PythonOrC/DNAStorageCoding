from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class ChannelParams:
    p_sub: float = 0.01
    p_del: float = 0.005
    p_ins: float = 0.005
    gc_ins_bias: float = 0.0
    gc_sub_bias: float = 0.0
    homopolymer_threshold: int = 4
    homopolymer_del_multiplier: float = 3.0


@dataclass(frozen=True)
class TwoStageChannelParams:
    synthesis: ChannelParams = field(default_factory=ChannelParams)
    sequencing: ChannelParams = field(
        default_factory=lambda: ChannelParams(p_sub=0.02, p_del=0.02, p_ins=0.02)
    )
    enabled: bool = True


@dataclass(frozen=True)
class SchemeParams:
    chunk_data_bytes: int = 1024
    marker: str = "ACGTACGTAC"
    marker_period: int = 40
    max_marker_edit_distance: int = 2
    rs_parity_bytes: int = 32
    replication: int = 2
    gc_target: float = 0.5


@dataclass(frozen=True)
class GridSpec:
    p_sub_list: tuple[float, ...] = tuple(round(i * 0.007142857, 6) for i in range(8))
    p_indel_list: tuple[float, ...] = tuple(
        round(i * 0.007142857, 6) for i in range(8)
    )
    replication_list: tuple[int, ...] = (1, 2, 3)


@dataclass(frozen=True)
class ExperimentConfig:
    schemes: tuple[str, ...] = ("s1", "s2", "s3")
    dataset: str = "random"
    size_mb: float = 1.0
    trials_per_cell: int = 200
    base_seed: int = 12345
    two_stage_channel: bool = True
    # <= 0 means auto; otherwise explicit worker count.
    n_workers: int = 0


@dataclass(frozen=True)
class OutputSpec:
    out_dir: str = "results"
    run_id: str = "latest"
    save_raw_parquet: bool = True


@dataclass(frozen=True)
class RunSpec:
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)
    scheme_params: SchemeParams = field(default_factory=SchemeParams)
    channel: TwoStageChannelParams = field(default_factory=TwoStageChannelParams)
    grid: GridSpec = field(default_factory=GridSpec)
    output: OutputSpec = field(default_factory=OutputSpec)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunSpec":
        exp_data = {k: v for k, v in data["experiment"].items()
                    if k in ExperimentConfig.__dataclass_fields__}
        exp = ExperimentConfig(**exp_data)
        scheme = SchemeParams(**data["scheme_params"])
        grid = GridSpec(
            p_sub_list=tuple(data["grid"]["p_sub_list"]),
            p_indel_list=tuple(data["grid"]["p_indel_list"]),
            replication_list=tuple(data["grid"]["replication_list"]),
        )
        channel = TwoStageChannelParams(
            synthesis=ChannelParams(**data["channel"]["synthesis"]),
            sequencing=ChannelParams(**data["channel"]["sequencing"]),
            enabled=data["channel"]["enabled"],
        )
        output = OutputSpec(**data["output"])
        return cls(experiment=exp, scheme_params=scheme, channel=channel, grid=grid, output=output)

    def save_json(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> "RunSpec":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


def default_run_spec() -> RunSpec:
    return RunSpec()
