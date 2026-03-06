from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run all FINAL_*.json configs sequentially (one at a time)."
    )
    parser.add_argument(
        "--configs-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing FINAL_*.json config files.",
    )
    parser.add_argument(
        "--python",
        type=str,
        default=sys.executable,
        help="Python executable to use for launching runs.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue to the next config if a run fails.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configs = sorted(args.configs_dir.glob("FINAL_R_*.json"))
    if not configs:
        print(f"No FINAL_R_*.json files found in: {args.configs_dir}")
        return 1

    print(f"Found {len(configs)} FINAL config files in {args.configs_dir}")
    for i, cfg in enumerate(configs, start=1):
        cmd = [
            args.python,
            "-m",
            "dna_storage_sim.cli",
            "run-grid",
            "--config",
            str(cfg),
        ]
        print(f"[{i}/{len(configs)}] {' '.join(cmd)}")
        if args.dry_run:
            continue
        result = subprocess.run(cmd, cwd=args.configs_dir.parent)
        if result.returncode != 0:
            print(f"FAILED ({result.returncode}): {cfg.name}")
            if not args.continue_on_error:
                return result.returncode
        else:
            print(f"OK: {cfg.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
