"""Tests for S7 parking-sleeve allocation."""
from __future__ import annotations

import math

import pytest

from renquant_strategy_104.parking_sleeve import (
    ParkingSleeveConfig,
    SleeveAllocation,
    compute_sleeve_allocation,
    shadow_log_entry,
)


# ── Config validation ─────────────────────────────────────────────────────

class TestParkingSleeveConfig:
    def test_defaults(self):
        cfg = ParkingSleeveConfig()
        assert cfg.enabled is False
        assert cfg.mode == "shadow"
        assert cfg.vehicle == "split"
        assert cfg.spy_fraction == 0.0
        assert cfg.sgov_fraction == 1.0
        assert cfg.max_sleeve_pct == 0.50
        assert cfg.reserve_pct == 0.05
        assert cfg.bear_sweep_off is True

    def test_from_dict(self):
        cfg = ParkingSleeveConfig.from_dict({
            "enabled": True, "mode": "shadow", "spy_fraction": 0.3, "sgov_fraction": 0.7,
            "unknown_key": "ignored",
        })
        assert cfg.enabled is True
        assert cfg.spy_fraction == 0.3
        assert cfg.sgov_fraction == 0.7

    def test_from_empty_dict(self):
        cfg = ParkingSleeveConfig.from_dict({})
        assert cfg == ParkingSleeveConfig()

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="mode"):
            ParkingSleeveConfig(mode="turbo")

    def test_invalid_vehicle(self):
        with pytest.raises(ValueError, match="vehicle"):
            ParkingSleeveConfig(vehicle="BTC")

    def test_fractions_must_sum_to_one(self):
        with pytest.raises(ValueError, match="must equal 1.0"):
            ParkingSleeveConfig(spy_fraction=0.3, sgov_fraction=0.3)

    def test_spy_fraction_out_of_range(self):
        with pytest.raises(ValueError, match="spy_fraction"):
            ParkingSleeveConfig(spy_fraction=-0.1, sgov_fraction=1.1)

    def test_max_sleeve_pct_out_of_range(self):
        with pytest.raises(ValueError, match="max_sleeve_pct"):
            ParkingSleeveConfig(max_sleeve_pct=1.5)

    def test_reserve_pct_out_of_range(self):
        with pytest.raises(ValueError, match="reserve_pct"):
            ParkingSleeveConfig(reserve_pct=-0.01)

    def test_live_spy_exposure_requires_gate_cleared(self):
        with pytest.raises(ValueError, match="spy_arm_gate_cleared"):
            ParkingSleeveConfig(enabled=True, mode="live", vehicle="SPY")

    def test_live_spy_exposure_via_split_fractions_requires_gate_cleared(self):
        # vehicle="split" with a nonzero spy_fraction is still SPY exposure —
        # the guard must catch it via the resolved fraction, not just vehicle="SPY".
        with pytest.raises(ValueError, match="spy_arm_gate_cleared"):
            ParkingSleeveConfig(
                enabled=True, mode="live",
                spy_fraction=0.3, sgov_fraction=0.7,
            )

    def test_live_spy_exposure_allowed_with_gate_cleared(self):
        cfg = ParkingSleeveConfig(
            enabled=True, mode="live", vehicle="SPY",
            spy_arm_gate_cleared=True,
        )
        assert cfg.spy_arm_gate_cleared is True

    def test_live_sgov_only_not_blocked_by_spy_guard(self):
        # SGOV-only live configs carry no SPY exposure — must not require the gate.
        cfg = ParkingSleeveConfig(enabled=True, mode="live", vehicle="SGOV")
        assert cfg.spy_arm_gate_cleared is False

    def test_shadow_mode_spy_exposure_not_blocked_by_spy_guard(self):
        # Shadow mode never places real orders — the gate only applies to live mode.
        cfg = ParkingSleeveConfig(enabled=True, mode="shadow", vehicle="SPY")
        assert cfg.spy_arm_gate_cleared is False

    def test_disabled_live_spy_not_blocked_by_spy_guard(self):
        # enabled=False never allocates — the gate only applies when actually enabled.
        cfg = ParkingSleeveConfig(enabled=False, mode="live", vehicle="SPY")
        assert cfg.spy_arm_gate_cleared is False


# ── Allocation logic ──────────────────────────────────────────────────────

class TestComputeSleeveAllocation:
    def test_disabled_returns_all_cash(self):
        cfg = ParkingSleeveConfig(enabled=False)
        alloc = compute_sleeve_allocation(50000, 100000, "BULL_CALM", cfg)
        assert alloc.spy_shares == 0
        assert alloc.sgov_shares == 0
        assert alloc.cash_remaining == 50000
        assert alloc.shadow is True
        assert alloc.sweep_reason == "disabled"

    def test_bear_sweep_returns_all_cash(self):
        cfg = ParkingSleeveConfig(enabled=True, bear_sweep_off=True)
        alloc = compute_sleeve_allocation(50000, 100000, "BEAR_CALM", cfg)
        assert alloc.cash_remaining == 50000
        assert alloc.sweep_reason == "bear_regime_sweep"

    def test_bear_sweep_off_false_allows_deployment(self):
        cfg = ParkingSleeveConfig(
            enabled=True, bear_sweep_off=False,
            spy_fraction=0.0, sgov_fraction=1.0,
        )
        alloc = compute_sleeve_allocation(
            50000, 100000, "BEAR_CALM", cfg,
            sgov_price=100.0,
        )
        assert alloc.sgov_shares > 0
        assert alloc.sweep_reason is None

    def test_all_sgov_default(self):
        cfg = ParkingSleeveConfig(enabled=True, mode="shadow")
        alloc = compute_sleeve_allocation(
            50000, 100000, "BULL_CALM", cfg,
            spy_price=550.0, sgov_price=100.0,
        )
        assert alloc.spy_shares == 0
        assert alloc.sgov_shares > 0
        assert alloc.shadow is True
        reserve = 100000 * 0.05
        deployable = min(50000 - reserve, 100000 * 0.50)
        expected_sgov = math.floor(deployable / 100.0)
        assert alloc.sgov_shares == expected_sgov

    def test_split_allocation(self):
        cfg = ParkingSleeveConfig(
            enabled=True, mode="live",
            spy_fraction=0.3, sgov_fraction=0.7,
            spy_arm_gate_cleared=True,
        )
        alloc = compute_sleeve_allocation(
            80000, 100000, "BULL_CALM", cfg,
            spy_price=550.0, sgov_price=100.0,
        )
        assert alloc.shadow is False
        assert alloc.spy_shares >= 0
        assert alloc.sgov_shares > 0
        assert alloc.cash_remaining >= 0

    def test_vehicle_spy_allocates_all_spy_regardless_of_fraction_fields(self):
        # Regression: vehicle="SPY" with UNTOUCHED (default) fraction fields
        # (spy_fraction=0.0, sgov_fraction=1.0) must still allocate all-SPY —
        # previously this silently allocated zero SPY / all SGOV.
        cfg = ParkingSleeveConfig(
            enabled=True, mode="live", vehicle="SPY",
            spy_arm_gate_cleared=True,
        )
        alloc = compute_sleeve_allocation(
            50000, 100000, "BULL_CALM", cfg,
            spy_price=550.0, sgov_price=100.0,
        )
        assert alloc.spy_shares > 0
        assert alloc.sgov_shares == 0

    def test_vehicle_sgov_allocates_all_sgov_regardless_of_fraction_fields(self):
        cfg = ParkingSleeveConfig(
            enabled=True, mode="live", vehicle="SGOV",
            spy_fraction=1.0, sgov_fraction=0.0,
        )
        alloc = compute_sleeve_allocation(
            50000, 100000, "BULL_CALM", cfg,
            spy_price=550.0, sgov_price=100.0,
        )
        assert alloc.spy_shares == 0
        assert alloc.sgov_shares > 0

    def test_vehicle_split_uses_explicit_fraction_fields(self):
        cfg = ParkingSleeveConfig(
            enabled=True, mode="live", vehicle="split",
            spy_fraction=0.3, sgov_fraction=0.7,
            spy_arm_gate_cleared=True,
        )
        alloc = compute_sleeve_allocation(
            80000, 100000, "BULL_CALM", cfg,
            spy_price=550.0, sgov_price=100.0,
        )
        assert alloc.spy_shares > 0
        assert alloc.sgov_shares > 0

    def test_max_sleeve_cap(self):
        cfg = ParkingSleeveConfig(
            enabled=True, max_sleeve_pct=0.10,
            spy_fraction=0.0, sgov_fraction=1.0,
        )
        alloc = compute_sleeve_allocation(
            90000, 100000, "BULL_CALM", cfg,
            sgov_price=100.0,
        )
        max_deploy = 100000 * 0.10
        assert alloc.sgov_notional <= max_deploy + 1e-6

    def test_reserve_floor(self):
        cfg = ParkingSleeveConfig(
            enabled=True, reserve_pct=0.10,
            spy_fraction=0.0, sgov_fraction=1.0,
        )
        alloc = compute_sleeve_allocation(
            12000, 100000, "BULL_CALM", cfg,
            sgov_price=100.0,
        )
        reserve = 100000 * 0.10
        deployable = 12000 - reserve
        expected = math.floor(deployable / 100.0)
        assert alloc.sgov_shares == expected

    def test_insufficient_cash(self):
        cfg = ParkingSleeveConfig(enabled=True, reserve_pct=0.50)
        alloc = compute_sleeve_allocation(
            100, 100000, "BULL_CALM", cfg,
            sgov_price=100.0,
        )
        assert alloc.sweep_reason == "insufficient_deployable"
        assert alloc.cash_remaining == 100

    def test_zero_portfolio_value(self):
        cfg = ParkingSleeveConfig(enabled=True)
        alloc = compute_sleeve_allocation(1000, 0, "BULL_CALM", cfg)
        assert alloc.sweep_reason == "zero_portfolio_value"

    def test_zero_price_skips_instrument(self):
        cfg = ParkingSleeveConfig(
            enabled=True,
            spy_fraction=0.5, sgov_fraction=0.5,
        )
        alloc = compute_sleeve_allocation(
            50000, 100000, "BULL_CALM", cfg,
            spy_price=0.0, sgov_price=100.0,
        )
        assert alloc.spy_shares == 0
        assert alloc.sgov_shares > 0

    def test_shadow_mode_stays_shadow(self):
        cfg = ParkingSleeveConfig(enabled=True, mode="shadow")
        alloc = compute_sleeve_allocation(
            50000, 100000, "BULL_CALM", cfg,
            sgov_price=100.0,
        )
        assert alloc.shadow is True

    def test_live_mode_not_shadow(self):
        cfg = ParkingSleeveConfig(enabled=True, mode="live")
        alloc = compute_sleeve_allocation(
            50000, 100000, "BULL_CALM", cfg,
            sgov_price=100.0,
        )
        assert alloc.shadow is False

    def test_whole_shares_rounding(self):
        cfg = ParkingSleeveConfig(
            enabled=True,
            spy_fraction=0.0, sgov_fraction=1.0,
        )
        alloc = compute_sleeve_allocation(
            50000, 100000, "BULL_CALM", cfg,
            sgov_price=99.99,
        )
        assert isinstance(alloc.sgov_shares, int)
        assert alloc.sgov_notional == alloc.sgov_shares * 99.99

    def test_sleeve_pct_computed(self):
        cfg = ParkingSleeveConfig(
            enabled=True,
            spy_fraction=0.0, sgov_fraction=1.0,
        )
        alloc = compute_sleeve_allocation(
            50000, 100000, "BULL_CALM", cfg,
            sgov_price=100.0,
        )
        assert 0 < alloc.sleeve_pct <= 0.50

    # ── Cross-session exposure cap (codex round-1 finding on #44) ────────
    #
    # max_sleeve_pct is documented/tested as a cap on TOTAL sleeve exposure,
    # but pre-fix, compute_sleeve_allocation had no input for sleeve value
    # already held from prior sessions — it could only cap THIS call's new
    # deployment, letting cumulative exposure drift past the configured cap
    # once repeated across sessions. These tests prove the cap now binds on
    # cumulative exposure, not just a single call in isolation.

    def test_current_sleeve_value_reduces_headroom(self):
        cfg = ParkingSleeveConfig(
            enabled=True, max_sleeve_pct=0.20,
            spy_fraction=0.0, sgov_fraction=1.0,
        )
        alloc = compute_sleeve_allocation(
            50000, 100000, "BULL_CALM", cfg,
            current_sleeve_value=15000.0,  # only 5000 of headroom left below the 20% cap
            sgov_price=100.0,
        )
        headroom = 100000 * 0.20 - 15000.0
        assert alloc.sgov_notional <= headroom + 1e-6

    def test_cap_already_reached_blocks_further_deployment(self):
        cfg = ParkingSleeveConfig(
            enabled=True, max_sleeve_pct=0.20,
            spy_fraction=0.0, sgov_fraction=1.0,
        )
        alloc = compute_sleeve_allocation(
            50000, 100000, "BULL_CALM", cfg,
            current_sleeve_value=20000.0,  # already at the 20% cap
            sgov_price=100.0,
        )
        assert alloc.sgov_shares == 0
        assert alloc.sweep_reason == "sleeve_cap_reached"

    def test_sleeve_pct_reflects_total_not_just_this_session(self):
        cfg = ParkingSleeveConfig(
            enabled=True, max_sleeve_pct=0.50,
            spy_fraction=0.0, sgov_fraction=1.0,
        )
        alloc = compute_sleeve_allocation(
            10000, 100000, "BULL_CALM", cfg,
            current_sleeve_value=20000.0,
            sgov_price=100.0,
        )
        expected_total = (20000.0 + alloc.sgov_notional) / 100000
        assert alloc.sleeve_pct == pytest.approx(expected_total)

    def test_repeated_sessions_never_exceed_cumulative_cap(self):
        """Simulate 3 sessions of fresh idle cash: the caller threads the
        prior session's deployed notional forward as current_sleeve_value,
        and cumulative sleeve exposure must never exceed the configured cap
        even though each session sees a large, independent cash_available.
        """
        cfg = ParkingSleeveConfig(
            enabled=True, max_sleeve_pct=0.20,
            spy_fraction=0.0, sgov_fraction=1.0,
        )
        portfolio_value = 100000
        cap = portfolio_value * cfg.max_sleeve_pct
        current_sleeve_value = 0.0

        alloc1 = compute_sleeve_allocation(
            80000, portfolio_value, "BULL_CALM", cfg,
            current_sleeve_value=current_sleeve_value, sgov_price=100.0,
        )
        current_sleeve_value += alloc1.sgov_notional
        assert current_sleeve_value <= cap + 1e-6

        alloc2 = compute_sleeve_allocation(
            50000, portfolio_value, "BULL_CALM", cfg,
            current_sleeve_value=current_sleeve_value, sgov_price=100.0,
        )
        current_sleeve_value += alloc2.sgov_notional
        assert current_sleeve_value <= cap + 1e-6

        alloc3 = compute_sleeve_allocation(
            50000, portfolio_value, "BULL_CALM", cfg,
            current_sleeve_value=current_sleeve_value, sgov_price=100.0,
        )
        current_sleeve_value += alloc3.sgov_notional
        assert current_sleeve_value <= cap + 1e-6
        # By session 3 the cap is exhausted — no further deployment allowed.
        assert alloc3.sgov_shares == 0
        assert alloc3.sweep_reason == "sleeve_cap_reached"


# ── Shadow log ────────────────────────────────────────────────────────────

class TestShadowLogEntry:
    def test_format(self):
        cfg = ParkingSleeveConfig(enabled=True)
        alloc = SleeveAllocation(sgov_shares=100, sgov_notional=10000, cash_remaining=40000, sleeve_pct=0.10)
        entry = shadow_log_entry(
            alloc, run_id="run-123", run_date="2026-07-04",
            regime="BULL_CALM", cash_available=50000, portfolio_value=100000,
            config=cfg,
        )
        assert entry["run_id"] == "run-123"
        assert entry["run_date"] == "2026-07-04"
        assert entry["regime"] == "BULL_CALM"
        assert entry["cash_pct"] == 0.5
        assert entry["allocation"]["sgov_shares"] == 100
        assert entry["config"]["enabled"] is True

    def test_zero_portfolio_value_cash_pct(self):
        cfg = ParkingSleeveConfig()
        alloc = SleeveAllocation(cash_remaining=0)
        entry = shadow_log_entry(
            alloc, "r", "d", "BULL_CALM", 0, 0, cfg,
        )
        assert entry["cash_pct"] == 0.0


# ── to_dict round-trip ────────────────────────────────────────────────────

def test_allocation_to_dict():
    alloc = SleeveAllocation(spy_shares=5, sgov_shares=100, cash_remaining=1234.56, shadow=True)
    d = alloc.to_dict()
    assert d["spy_shares"] == 5
    assert d["sgov_shares"] == 100
    assert d["cash_remaining"] == 1234.56
    assert d["shadow"] is True
