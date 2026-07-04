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
        )
        alloc = compute_sleeve_allocation(
            80000, 100000, "BULL_CALM", cfg,
            spy_price=550.0, sgov_price=100.0,
        )
        assert alloc.shadow is False
        assert alloc.spy_shares >= 0
        assert alloc.sgov_shares > 0
        assert alloc.cash_remaining >= 0

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
