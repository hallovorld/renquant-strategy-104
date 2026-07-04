"""S7 parking-sleeve allocation — shadow-first, default-OFF.

Computes how idle cash would be deployed into a market-tracking (SPY) and/or
risk-free (SGOV) sleeve.  The allocation is computed every session but only
*logged* until live-mode is explicitly authorized via a preregistered gate
(RS-1 is PROVISIONAL as of 2026-07-04).

Design: doc/research/2026-07-02-rs1-parking-sleeve.md
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass(frozen=True)
class ParkingSleeveConfig:
    enabled: bool = False
    mode: str = "shadow"
    vehicle: str = "split"
    spy_fraction: float = 0.0
    sgov_fraction: float = 1.0
    max_sleeve_pct: float = 0.50
    reserve_pct: float = 0.05
    bear_sweep_off: bool = True
    spy_arm_gate_cleared: bool = False

    def __post_init__(self) -> None:
        if self.mode not in ("shadow", "live"):
            raise ValueError(f"parking_sleeve.mode must be 'shadow' or 'live', got {self.mode!r}")
        if self.vehicle not in ("SPY", "SGOV", "split"):
            raise ValueError(f"parking_sleeve.vehicle must be SPY/SGOV/split, got {self.vehicle!r}")
        if not 0.0 <= self.spy_fraction <= 1.0:
            raise ValueError(f"spy_fraction must be in [0, 1], got {self.spy_fraction}")
        if not 0.0 <= self.sgov_fraction <= 1.0:
            raise ValueError(f"sgov_fraction must be in [0, 1], got {self.sgov_fraction}")
        if abs(self.spy_fraction + self.sgov_fraction - 1.0) > 1e-9:
            raise ValueError(
                f"spy_fraction + sgov_fraction must equal 1.0, "
                f"got {self.spy_fraction} + {self.sgov_fraction} = {self.spy_fraction + self.sgov_fraction}"
            )
        if not 0.0 <= self.max_sleeve_pct <= 1.0:
            raise ValueError(f"max_sleeve_pct must be in [0, 1], got {self.max_sleeve_pct}")
        if not 0.0 <= self.reserve_pct <= 1.0:
            raise ValueError(f"reserve_pct must be in [0, 1], got {self.reserve_pct}")

        # RS-1 (doc/research/2026-07-02-rs1-parking-sleeve.md) is PROVISIONAL:
        # the SPY arm specifically requires its own preregistered gate before
        # any capital exposure. A config that is enabled+live+SPY-exposed
        # must not be constructible without an explicit acknowledgement that
        # gate has actually cleared — this is a structural guard, not a
        # substitute for the real authorization artifact.
        effective_spy_fraction, _ = resolve_vehicle_fractions(
            self.vehicle, self.spy_fraction, self.sgov_fraction
        )
        if (
            self.enabled
            and self.mode == "live"
            and effective_spy_fraction > 0
            and not self.spy_arm_gate_cleared
        ):
            raise ValueError(
                "parking_sleeve: live mode with SPY exposure "
                f"(vehicle={self.vehicle!r}, effective spy_fraction={effective_spy_fraction}) "
                "requires spy_arm_gate_cleared=True — RS-1's SPY arm is PROVISIONAL "
                "pending its own preregistered gate (doc/research/2026-07-02-rs1-parking-sleeve.md); "
                "do not set this without the real authorization in hand."
            )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ParkingSleeveConfig":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


def resolve_vehicle_fractions(
    vehicle: str, spy_fraction: float, sgov_fraction: float
) -> tuple[float, float]:
    """Resolve the effective (spy_fraction, sgov_fraction) for a config.

    ``vehicle`` is the real source of truth: "SPY"/"SGOV" force a pure
    single-vehicle allocation regardless of the fraction fields; "split"
    defers to the explicit fraction fields (the blended-ratio override,
    e.g. the RS-1 30/70 planning heuristic).
    """
    if vehicle == "SPY":
        return 1.0, 0.0
    if vehicle == "SGOV":
        return 0.0, 1.0
    return spy_fraction, sgov_fraction


@dataclass
class SleeveAllocation:
    spy_shares: int = 0
    sgov_shares: int = 0
    spy_notional: float = 0.0
    sgov_notional: float = 0.0
    cash_remaining: float = 0.0
    sleeve_pct: float = 0.0
    shadow: bool = True
    sweep_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_sleeve_allocation(
    cash_available: float,
    portfolio_value: float,
    regime: str,
    config: ParkingSleeveConfig,
    spy_price: float = 0.0,
    sgov_price: float = 0.0,
) -> SleeveAllocation:
    """Compute parking-sleeve allocation from idle cash.

    Returns a SleeveAllocation that is always shadow=True unless config.mode
    is "live" AND config.enabled is True.  Even then, this function only
    COMPUTES — it never places orders.
    """
    is_shadow = not config.enabled or config.mode != "live"

    if not config.enabled:
        return SleeveAllocation(
            cash_remaining=cash_available,
            shadow=True,
            sweep_reason="disabled",
        )

    if config.bear_sweep_off and regime.startswith("BEAR"):
        return SleeveAllocation(
            cash_remaining=cash_available,
            shadow=is_shadow,
            sweep_reason="bear_regime_sweep",
        )

    if portfolio_value <= 0:
        return SleeveAllocation(
            cash_remaining=cash_available,
            shadow=is_shadow,
            sweep_reason="zero_portfolio_value",
        )

    reserve = portfolio_value * config.reserve_pct
    deployable = max(0.0, cash_available - reserve)

    max_sleeve = portfolio_value * config.max_sleeve_pct
    deployable = min(deployable, max_sleeve)

    if deployable < 1.0:
        return SleeveAllocation(
            cash_remaining=cash_available,
            shadow=is_shadow,
            sweep_reason="insufficient_deployable",
        )

    spy_fraction, sgov_fraction = resolve_vehicle_fractions(
        config.vehicle, config.spy_fraction, config.sgov_fraction
    )
    spy_target = deployable * spy_fraction
    sgov_target = deployable * sgov_fraction

    spy_shares = 0
    spy_notional = 0.0
    if spy_price > 0 and spy_target > 0:
        spy_shares = math.floor(spy_target / spy_price)
        spy_notional = spy_shares * spy_price

    sgov_shares = 0
    sgov_notional = 0.0
    if sgov_price > 0 and sgov_target > 0:
        sgov_shares = math.floor(sgov_target / sgov_price)
        sgov_notional = sgov_shares * sgov_price

    total_deployed = spy_notional + sgov_notional
    cash_remaining = cash_available - total_deployed
    sleeve_pct = total_deployed / portfolio_value if portfolio_value > 0 else 0.0

    return SleeveAllocation(
        spy_shares=spy_shares,
        sgov_shares=sgov_shares,
        spy_notional=spy_notional,
        sgov_notional=sgov_notional,
        cash_remaining=cash_remaining,
        sleeve_pct=sleeve_pct,
        shadow=is_shadow,
    )


def shadow_log_entry(
    allocation: SleeveAllocation,
    run_id: str,
    run_date: str,
    regime: str,
    cash_available: float,
    portfolio_value: float,
    config: ParkingSleeveConfig,
) -> dict[str, Any]:
    """Format a JSONL shadow log entry for the parking sleeve."""
    return {
        "run_id": run_id,
        "run_date": run_date,
        "regime": regime,
        "cash_available": cash_available,
        "portfolio_value": portfolio_value,
        "cash_pct": cash_available / portfolio_value if portfolio_value > 0 else 0.0,
        "config": asdict(config),
        "allocation": allocation.to_dict(),
    }
