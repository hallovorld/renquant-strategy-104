"""Config drift detection for RenQuant 104 strategy configs."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_IGNORES = {
    "ranking.blend_n_symbols",
    "ranking.blend_weights.rank",
    "ranking.blend_weights.rs",
}


def _walk(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dict into dotted paths. Lists stay as values."""
    flat: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(child, dict):
                flat.update(_walk(child, path))
            else:
                flat[path] = child
    return flat


def _bool_drift(baseline: bool | None, live: bool | None) -> str | None:
    if baseline == live:
        return None
    if baseline is False and live is True:
        return "false -> true (flag quietly enabled)"
    if baseline is None and live is True:
        return "(absent) -> true (new flag enabled)"
    return f"{baseline} -> {live}"


def _numeric_drift(
    baseline: float | None,
    live: float | None,
    tolerance: float,
) -> str | None:
    if baseline is None or live is None:
        return None
    if baseline == live:
        return None
    if baseline == 0:
        return f"{baseline} -> {live}" if live != 0 else None
    pct = abs((live - baseline) / baseline)
    if pct >= tolerance:
        return f"{baseline} -> {live}  ({pct * 100:+.1f}%)"
    return None


def resolve_repo_root(value: str | Path | None = None) -> Path:
    candidate = value or os.environ.get("RENQUANT_REPO_ROOT") or Path.cwd()
    return Path(candidate).expanduser().resolve()


def resolve_config_root(
    *,
    repo_root: Path,
    strategy: str,
    config_root: str | Path | None,
) -> Path:
    if config_root is not None:
        return Path(config_root).expanduser().resolve()
    umbrella_dir = repo_root / "backtesting" / strategy
    if umbrella_dir.exists():
        return umbrella_dir
    return repo_root / "configs"


def find_drifts(
    baseline: dict[str, Any],
    live: dict[str, Any],
    *,
    numeric_tolerance: float = 0.10,
    ignore_paths: set[str] | None = None,
    use_default_ignores: bool = True,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    ignored = set(ignore_paths or set())
    if use_default_ignores:
        ignored |= DEFAULT_IGNORES

    b_flat = _walk(baseline)
    l_flat = _walk(live)
    bool_drifts: list[tuple[str, str]] = []
    num_drifts: list[tuple[str, str]] = []

    for key in sorted(set(b_flat) | set(l_flat)):
        if key in ignored:
            continue
        b_value = b_flat.get(key)
        l_value = l_flat.get(key)
        if isinstance(b_value, bool) or isinstance(l_value, bool):
            drift = _bool_drift(b_value, l_value)
            if drift:
                bool_drifts.append((key, drift))
        elif isinstance(b_value, (int, float)) and isinstance(l_value, (int, float)):
            drift = _numeric_drift(float(b_value), float(l_value), numeric_tolerance)
            if drift:
                num_drifts.append((key, drift))

    return bool_drifts, num_drifts


def run_check(
    *,
    config_root: Path,
    baseline_name: str,
    live_name: str,
    numeric_tolerance: float,
    ignore_paths: set[str],
    use_default_ignores: bool,
) -> tuple[int, str]:
    baseline_path = config_root / baseline_name
    live_path = config_root / live_name
    if not baseline_path.exists():
        return 1, f"ERROR: baseline missing: {baseline_path}"
    if not live_path.exists():
        return 1, f"ERROR: live missing: {live_path}"

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    live = json.loads(live_path.read_text(encoding="utf-8"))
    bool_drifts, num_drifts = find_drifts(
        baseline,
        live,
        numeric_tolerance=numeric_tolerance,
        ignore_paths=ignore_paths,
        use_default_ignores=use_default_ignores,
    )
    if not bool_drifts and not num_drifts:
        return 0, f"Config drift check OK: {live_name} matches {baseline_name}."

    lines = [f"Config drift detected in {live_path.name} vs {baseline_path.name}:", ""]
    if bool_drifts:
        lines.append("Boolean flag changes:")
        lines.extend(f"  {key}: {desc}" for key, desc in bool_drifts)
        lines.append("")
    if num_drifts:
        lines.append(f"Numeric changes (tolerance {numeric_tolerance * 100:.0f}%):")
        lines.extend(f"  {key}: {desc}" for key, desc in num_drifts)
        lines.append("")
    lines.append("If these changes are intentional:")
    lines.append("  1. Update strategy_config.golden.json (promote), or")
    lines.append("  2. Revert strategy_config.json if drift is unintended.")
    return 1, "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=None,
                        help="Umbrella RenQuant repo root. Defaults to RENQUANT_REPO_ROOT or cwd.")
    parser.add_argument("--strategy", default="renquant_104")
    parser.add_argument("--config-root", default=None,
                        help="Explicit directory containing strategy_config*.json.")
    parser.add_argument("--numeric-tolerance", type=float, default=0.10,
                        help="Flag numeric changes at or above this fraction.")
    parser.add_argument("--ignore-path", action="append", default=[],
                        help="Dotted config path to skip; can repeat.")
    parser.add_argument("--no-default-ignores", action="store_true",
                        help="Disable built-in ignores for daily recalibration fields.")
    parser.add_argument("--baseline", default="strategy_config.golden.json")
    parser.add_argument("--live", default="strategy_config.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = resolve_repo_root(args.repo_root)
    config_root = resolve_config_root(
        repo_root=repo_root,
        strategy=args.strategy,
        config_root=args.config_root,
    )
    code, message = run_check(
        config_root=config_root,
        baseline_name=args.baseline,
        live_name=args.live,
        numeric_tolerance=args.numeric_tolerance,
        ignore_paths=set(args.ignore_path),
        use_default_ignores=not args.no_default_ignores,
    )
    print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
