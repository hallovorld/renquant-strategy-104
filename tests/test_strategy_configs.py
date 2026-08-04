from __future__ import annotations

import json
from pathlib import Path

import pytest

from renquant_strategy_104 import load_strategy_config, strategy_manifest


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"
LATEST_PRODUCTION_SYNC_SOURCE = "732704bdb00c5bda6a9f6a4ee4c33523c0824286"


def _load(name: str) -> dict:
    return json.loads((CONFIG_DIR / name).read_text())


def test_required_policy_configs_exist_and_parse() -> None:
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
        "strategy_config.shadow_a.json",
        "strategy_config.shadow_b.json",
        "strategy_config.shadow_blend.json",
        "strategy_config.shadow_blend_momentum.json",
        "xgb_prod_artifact_manifest.json",
    ):
        data = _load(name)
        assert isinstance(data, dict)
        if name.startswith("strategy_config"):
            assert data.get("watchlist"), f"{name} missing watchlist"
            assert data.get("regime_params"), f"{name} missing regime_params"


def test_active_and_golden_watchlist_match() -> None:
    active = _load("strategy_config.json")
    golden = _load("strategy_config.golden.json")
    assert active["watchlist"] == golden["watchlist"]


def test_active_and_golden_semantic_config_match() -> None:
    active = _load("strategy_config.json")
    golden = _load("strategy_config.golden.json")

    active_norm = _strip_provenance(active)
    golden_norm = _strip_provenance(golden)
    # Production active currently carries the selected WF manifest; golden
    # remains the policy baseline. Keep that explicit rather than blocking the
    # production sync.
    active_wf = active_norm.pop("walkforward", None)
    golden_wf = golden_norm.pop("walkforward", None)
    assert active_wf == {
        "manifest_path": (
            "/Users/renhao/git/github/RenQuant/backtesting/renquant_104/"
            "artifacts/sim/walkforward_manifest_dropsenti_v3.json"
        )
    }
    assert golden_wf is None
    assert active_norm == golden_norm


def test_cash_drag_slot_counts_stay_at_production_8_3() -> None:
    """Pin the production slot counts so the 2026-06-29 cash-drag analysis
    (PR #35) stays PROPOSAL-ONLY and cannot silently raise live policy.

    A real 2026-06-29 daily-full deployed only $827 of $8,730 buying power
    (live book ~46% deployed) because two slot caps -- top-level
    max_concurrent_positions and rotation.panel_buy_top_n -- bounded how many
    small positions the book can hold. A readonly 8/3 vs 10/4 replay run today
    on the live book showed the slot-raise is a WEAK fix: 10/4 deploys only
    ~$427 more (CVX + ZM) while the genuinely better high-price names
    (AVGO/BLK/GS) were selected but skipped by whole-share rounding because
    their Kelly targets (~$400, ~4%) are smaller than one share. The real lever
    is FRACTIONAL SHARES, not slot count, so active/golden stay at the
    production 8/3 and this PR merges as the analysis record only. See
    doc/design/2026-06-29-cash-drag-raise-slots.md. Active and golden must
    agree for the CI semantic-match contract."""
    active = _load("strategy_config.json")
    golden = _load("strategy_config.golden.json")

    assert active["max_concurrent_positions"] == 8
    assert golden["max_concurrent_positions"] == 8
    assert active["rotation"]["panel_buy_top_n"] == 3
    assert golden["rotation"]["panel_buy_top_n"] == 3
    assert (
        active["max_concurrent_positions"]
        == golden["max_concurrent_positions"]
    )
    assert (
        active["rotation"]["panel_buy_top_n"]
        == golden["rotation"]["panel_buy_top_n"]
    )

    # Per-name and per-sector risk and Kelly aggression are deliberately NOT
    # touched -- guard against an accidental risk relaxation.
    assert active["ranking"]["kelly_sizing"]["fractional"] == 0.3
    assert active["ranking"]["kelly_sizing"]["max_concentration"] == 0.12
    assert active["regime_params"]["BULL_CALM"]["max_position_pct"] == 0.12
    assert active["max_positions_per_sector"] == 6


def test_conviction_gate_demean_is_off_and_mu_floor_pinned() -> None:
    """Pin the conviction-gate intent so it cannot silently drift (PR #34 /
    2026-06-29 emergency revert). demean_cross_sectional MUST be false in both
    active and golden — with demean ON the absolute mu_floor=0.03 is applied to a
    relative (demeaned) quantity, which on the fresh fundamentals feed admitted
    ZERO names (run 2026-06-29-live-5970796e: max mu 0.0505, xs_mean +0.0212, so
    even the top name demeaned to 0.0293 < 0.03). mu_floor stays 0.03 on raw mu."""
    for name in ("strategy_config.json", "strategy_config.golden.json"):
        cfg = load_strategy_config(CONFIG_DIR / name)
        gate = cfg["ranking"]["panel_scoring"]["conviction_gate"]
        assert gate["enabled"] is True
        assert gate["demean_cross_sectional"] is False, (
            f"{name}: demean_cross_sectional must be false (emergency revert PR #34)"
        )
        assert gate["mu_floor"] == 0.03, f"{name}: mu_floor must stay 0.03"


def test_sector_map_covers_active_watchlist() -> None:
    cfg = _load("strategy_config.json")
    sector_map = cfg.get("sector_map", {})
    missing = sorted(t for t in cfg["watchlist"] if t not in sector_map)
    assert missing == []


def test_watchlist_is_unique_and_contains_benchmark() -> None:
    cfg = _load("strategy_config.json")

    assert len(cfg["watchlist"]) == len(set(cfg["watchlist"]))
    assert cfg["benchmark"] in cfg["watchlist"]


def test_bull_calm_new_buys_and_panel_scorer_contract_are_explicit() -> None:
    cfg = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    shadow = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")
    panel = cfg["ranking"]["panel_scoring"]
    global_cal = panel["global_calibration"]

    assert cfg["regime_params"]["BULL_CALM"]["disable_new_buys"] is False
    assert panel["enabled"] is True
    assert panel["kind"] == "xgb"
    assert panel["artifact_path"] == "artifacts/prod/panel-ltr.alpha158_fund.json"
    assert global_cal["enabled"] is True
    assert global_cal["strict_scorer_match"] is True
    assert global_cal["artifact_path"] == "artifacts/prod/panel-rank-calibration.json"
    # Conviction gate (renquant-pipeline #140) is the quality guard that makes the
    # XGB primary deployable: only buy calibrated E[R-SPY] >= 3%.
    assert panel["conviction_gate"]["enabled"] is True
    assert panel["conviction_gate"]["mu_floor"] == 0.03
    assert panel["regime_admission"]["enabled"] is False
    # Legacy ops-shadow file (strategy_config.shadow.json) still carries the
    # PatchTST full-config; the orch#741 retirement removed the SERVED
    # shadow_models lane from the prod/golden configs, and deliberately did
    # not touch this standalone file (see doc/progress/2026-08-02).
    assert shadow["ranking"]["panel_scoring"]["kind"] == "hf_patchtst"
    assert "patchtst_shadow" in shadow["ranking"]["panel_scoring"]["artifact_path"]


def test_panel_watchlist_candidate_universe_is_shadow_only() -> None:
    """A broader candidate entry rule is measurable before any live promotion."""
    production = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    golden = load_strategy_config(CONFIG_DIR / "strategy_config.golden.json")
    shadow = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")

    assert production["ranking"]["panel_scoring"].get("candidate_universe") is None
    assert golden["ranking"]["panel_scoring"].get("candidate_universe") is None
    assert shadow["ranking"]["panel_scoring"]["candidate_universe"] == "watchlist"


def test_xgb_operator_promotion_contract_is_auditable() -> None:
    cfg = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    golden = load_strategy_config(CONFIG_DIR / "strategy_config.golden.json")
    shadow = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")
    panel = cfg["ranking"]["panel_scoring"]
    golden_panel = golden["ranking"]["panel_scoring"]
    shadow_panel = shadow["ranking"]["panel_scoring"]

    promotion_note = panel.get("_2026_06_23_xgb_promotion", "")
    assert "operator-directed prod/shadow switch" in promotion_note
    assert "XGB" in promotion_note
    assert "PatchTST moved to readonly shadow" in promotion_note

    assert panel["kind"] == golden_panel["kind"] == "xgb"
    assert panel["artifact_path"] == golden_panel["artifact_path"]
    assert panel["artifact_path"] == "artifacts/prod/panel-ltr.alpha158_fund.json"
    assert panel["global_calibration"] == golden_panel["global_calibration"]
    assert panel["global_calibration"]["strict_scorer_match"] is True
    assert (
        panel["global_calibration"]["artifact_path"]
        == "artifacts/prod/panel-rank-calibration.json"
    )
    assert panel["conviction_gate"]["mu_floor"] == 0.03
    assert panel["regime_admission"]["enabled"] is False
    assert (
        "XGB trades ALL regimes"
        in panel["regime_admission"]["_promotion_reason_2026_06_23"]
    )

    # orch#741 retirement: the served hf_patchtst shadow lane is GONE from
    # shadow_models (in prod AND golden), the retirement narrative key exists
    # in both, and prod/golden stay consistent. Three lanes remain: the clf
    # blend leg (live), the slow momentum lane (GOAL-7 slice 4, live since
    # the 2026-08-02 grant batch), and the FAST momentum lane
    # (renquant-model#199 item 3 — PENDING its first weekly publish, see
    # PENDING_FIRST_ARTIFACT at the end of this file).
    for cfg_panel in (panel, golden_panel):
        assert all(
            m["name"] != "hf_patchtst_pt07_strict_seed44_previous_primary"
            for m in cfg_panel.get("shadow_models") or []
        )
        retirement_note = cfg_panel["_2026_08_02_patchtst_retirement"]
        assert "retired per orch#741" in retirement_note
        assert "PERSISTENCE-DRIVEN" in retirement_note
        assert "fresh candidate" in retirement_note
    assert panel["shadow_models"] == golden_panel["shadow_models"]
    assert (
        panel["_2026_08_02_patchtst_retirement"]
        == golden_panel["_2026_08_02_patchtst_retirement"]
    )

    shadow_models = panel.get("shadow_models") or []
    assert shadow_models == [
        {
            "name": "topdecile_clf_blend_leg",
            "kind": "xgb",
            "artifact_path": "artifacts/shadow/panel-clf.top-decile.fwd60.json",
            "expected_content_sha256": "sha256:1e644354e0981f47",
            "expected_config_fingerprint": "sha256:1d8f167fed18cd8cb1e0760251fdd5398724e630462d92b41561d2e19973e41b",
            "_2026_07_26_role": "clf leg of the CONFIRMED blend objective (model#74/75/76); scores = P(top decile fwd_60d_excess); blend computed OFFLINE by the readout job; governed by pipeline#213 frozen forward readout; NOT a production scorer",
            "_2026_07_26_operator_activation": "operator-directed shadow-slot activation; executed by the claude agent under explicit in-session operator delegation (2026-07-26) after the operator-run command block failed twice to terminal paste mangling; see PR body and doc/progress/2026-07-26-operator-delegated-activation.md for the verbatim grant",
            "_2026_07_27_restamp": "artifact re-stamped with effective_train_cutoff_date=2026-04-28 (model#83; missing_train_cutoff health fix); booster byte-identical, predictions identical, config_fingerprint unchanged",
            "_2026_07_28_recipe_restamp": "adds provenance_schema_version/recipe_id/required_axis_fields (walkforward_only_v1, common#36+model#84); booster/predictions/fp unchanged",
        },
        {
            "name": "momentum_residual_v0_shadow",
            "kind": "momentum_residual",
            "artifact_path": "artifacts/momentum/momentum_artifact_ledger.jsonl",
            "_2026_08_02_momentum_shadow_lane": "TRADE slice of the standalone momentum pipeline — design model#195 (doc/design/2026-08-02-momentum-pipeline-architecture.md §3), build-order amendment model#197, weekly TRAIN job surface orch#757. The job publishes artifacts/momentum/<cutoff>/momentum_residual_v0.json (artifact kind momentum_residual_v0, one dated artifact per weekly cutoff) PLUS the append-only digest-chained ledger this artifact_path pins — the one cutoff-stable file in the publish set, strategy_dir-relative under the same canonical resolver base as the blend leg's artifacts/shadow path. Serving-handler contract (config kind momentum_residual; pipeline-side registration pending): read the verified ledger tail row, load the dated artifact it names beside the ledger, verify its self-carried content_sha256 — each week's artifact serves with zero weekly config churn and the ledger chain transitively pins every served artifact. Shadow = data collection, no verdict claimed; promotion via the standard gates (WF lineage + freshness + operator sign-off).",
            "_2026_08_02_machine_produced_ledger": "run-surface state: the weekly TRAIN job publishes the ledger + dated artifacts on the serving machine (orch#757); they are never committed, so hosted CI runners cannot resolve this path BY DESIGN. The umbrella gate admits exactly this declared state as INFO (RenQuant#557, inside #554's momentum-contract narrowing) and still runs full chain verification wherever the ledger resolves. Distinct from the retired pending-first-artifact marker, which meant 'not published anywhere yet' (retired in #78 after the first publish).",
        },
        {
            "name": "momentum_fast_v1_shadow",
            "kind": "momentum_residual",
            "artifact_path": "artifacts/momentum_fast/momentum_artifact_ledger.jsonl",
            "_2026_08_03_fast_momentum_shadow_lane": "FAST clock of the SAME residual-momentum construction (window 63, skip 5; params frozen in renquant-model#199 BEFORE any production run; artifact kind momentum_residual_v1_fast — model#200 derives kind from params_version). Produced by the SAME weekly Saturday TRAIN job as the v0 lane (#199 build item 2: the orchestrator wrapper runs the train CLI a second, NON-FATAL time with --params-version v1_fast) into its OWN append-only digest-chained ledger — this artifact_path — with dated artifacts beside it per cutoff. Serving contract identical to the v0 entry (kind momentum_residual: verified ledger tail -> dated artifact -> content_sha256 + row/artifact cross-field parity + golden reproduction). The dated basename stays momentum_residual_v0.json in this lane too: the pipeline loader hardcodes it (momentum_residual_scorer.MOMENTUM_DATED_ARTIFACT_BASENAME) — a path convention, not an identity claim; identity is kind/params_version/content_sha256, which are v1_fast here (pipeline follow-up: derive the basename from the ledger row). Shadow = data collection for the operator's daily fast-momentum patrol (#199); no verdict claimed; promotion via the standard gates.",
            "_2026_08_03_pending_first_artifact": "declared dormant state, BOUNDED by tests/test_strategy_configs.py PENDING_FIRST_ARTIFACT (the v0 precedent, retired there in #78 after the first publish): until the deployed weekly job's first fast-lane run publishes this ledger, the path resolves NOWHERE — the daily shadow record for this lane is the unresolved-artifact NOT-LOADED record (artifact_resolved false, load_error 'did not resolve to an existing file'; pipeline shadow_scoring), NOT the not_yet_published expected skip, which requires an existing chain-verified zero-row ledger. Delete this key and shrink the named set in the SAME change once the first fast artifact + genesis row are published.",
        },
    ]
    assert (
        panel["shadow_experiment"]
        == "renquant_104_patchtst_shadow_after_xgb_promotion"
    )
    assert shadow_panel["kind"] == "hf_patchtst"
    assert "patchtst_shadow" in shadow_panel["artifact_path"]
    assert "production primary is XGB" in shadow["ranking"].get(
        "_2026_06_23_shadow_switch", ""
    )


def test_xgb_prod_artifact_manifest_matches_runtime_configs() -> None:
    cfg = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    golden = load_strategy_config(CONFIG_DIR / "strategy_config.golden.json")
    shadow = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")
    manifest = _load("xgb_prod_artifact_manifest.json")
    panel = cfg["ranking"]["panel_scoring"]
    golden_panel = golden["ranking"]["panel_scoring"]
    shadow_panel = shadow["ranking"]["panel_scoring"]
    primary = manifest["production_primary"]
    primary_cal = primary["global_calibration"]

    assert manifest["schema_version"] == 1
    assert manifest["strategy"] == "renquant_104"
    assert manifest["manifest_role"] == "operator_override_directive_audit"
    assert manifest["promotion_boundary"]["decision"] == (
        "operator_directed_prod_shadow_switch"
    )
    assert manifest["promotion_boundary"]["primary_model_family"] == "xgb"
    assert manifest["promotion_boundary"]["acceptance_status"] == (
        "operator_override_with_residual_controls"
    )

    # Scope is narrowed to an exceptional, withdrawable override — NOT a promotion.
    scope = manifest["scope_claim"]
    assert "operator directive" in scope["this_is"]
    assert "normal production promotion" in scope["this_is_not"]
    assert scope["positive_claims_only"] and scope["explicitly_not_claimed"]
    assert any("does not" in c.lower() for c in scope["explicitly_not_claimed"])

    assert primary["kind"] == panel["kind"] == golden_panel["kind"] == "xgb"
    assert primary["artifact_path"] == panel["artifact_path"] == golden_panel["artifact_path"]
    assert primary["artifact_path_role"] == "production_primary"

    runtime_cal = panel["global_calibration"]
    assert primary_cal["enabled"] == runtime_cal["enabled"] is True
    assert primary_cal["strict_scorer_match"] == runtime_cal["strict_scorer_match"] is True
    assert primary_cal["artifact_path"] == runtime_cal["artifact_path"]
    assert primary_cal["artifact_path"] == golden_panel["global_calibration"]["artifact_path"]
    assert primary_cal["artifact_path_role"] == "production_primary_calibrator"

    assert primary["conviction_gate"]["mu_floor"] == panel["conviction_gate"]["mu_floor"] == 0.03
    assert primary["regime_admission"]["enabled"] == panel["regime_admission"]["enabled"] is False

    # orch#741 retirement: the readonly_shadow (hf_patchtst) entry is removed
    # from the manifest and replaced by the retirement narrative key. The
    # legacy ops-shadow FILE is untouched (see the shadow_panel pins above);
    # only the manifest's current-state listing of the lane is retired.
    assert "readonly_shadow" not in manifest
    manifest_retirement = manifest["_2026_08_02_patchtst_retirement"]
    assert "retired per orch#741" in manifest_retirement
    assert "hf_patchtst_pt07_strict_seed44_previous_primary" in manifest_retirement
    assert shadow_panel["kind"] == "hf_patchtst"

    # The override is honestly recorded: XGB did not pass the gate; risks disclosed.
    assert "conviction_gate mu_floor 0.03" in manifest["residual_controls"]
    assert "calibrator strict_scorer_match" in manifest["residual_controls"]
    assert any("FAILED the WF promotion gate" in r for r in manifest["disclosed_risks"])
    assert any("Lags SPY" in r for r in manifest["disclosed_risks"])
    assert any(
        "Strengthen the BULL_CALM" in c for c in manifest["follow_up_exit_criteria"]
    )
    # Path B evidence: threshold sensitivity + honest caveat + concrete withdrawal trigger.
    assert "mu_floor_evidence" in manifest
    assert "coarse quality filter" in manifest["mu_floor_evidence"]["honest_caveat"].lower() \
        or "COARSE QUALITY FILTER" in manifest["mu_floor_evidence"]["honest_caveat"]
    assert manifest["mu_floor_evidence"]["threshold_sensitivity_top_of_cross_section"]["mu_by_name"]["CRWD"] == 0.053
    assert any("regime_admission" in t for t in manifest["override_withdrawal_trigger"])


def test_execution_contract_is_explicit() -> None:
    cfg = load_strategy_config(CONFIG_DIR / "strategy_config.json")

    assert cfg["execution"]["enabled"] is True
    assert cfg["execution"]["t2_settlement_days"] == 1
    assert cfg["execution"]["buying_power_mode"] == "non_marginable_buying_power"


def test_fractional_shares_contract_is_explicit_and_default_off() -> None:
    """S-FRAC v2 stage-2 config companion (renquant-pipeline #153; cash-drag
    phase-1 order in doc/design/2026-07-07-104-105-cash-drag-resolution.md).

    The block exists so fractional-sizing policy is declared in strategy
    config rather than living only in pipeline defaults, but it stays inert
    until the active-path capability gate, broker guard, and sizing-fidelity
    evidence are all proven. While disabled, 104 remains on the safe
    whole-share + A-3 fallback path."""
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        frac = cfg["execution"]["fractional_shares"]
        assert frac["enabled"] is False, f"{name}: fractional sizing must stay default-OFF"
        assert frac["min_notional"] == 1.0
        assert frac["min_fractional_trade_notional"] == 25.0
        assert frac["non_fractionable_tickers"] == []
        assert "#153" in frac["_comment"], f"{name}: must cite renquant-pipeline #153"
        assert "sizing-fidelity evidence" in frac["_comment"], (
            f"{name}: enablement bar must be explained"
        )
        assert "2026-07-07 cash-drag phase-1" in frac["_provenance"]
        assert set(frac) == {
            "enabled",
            "min_notional",
            "min_fractional_trade_notional",
            "non_fractionable_tickers",
            "_comment",
            "_provenance",
        }, f"{name}: unexpected fractional_shares keys"


def test_qp_cap_compliance_sells_are_enabled_without_relaxing_c2() -> None:
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        qp = cfg["rotation"]["joint_actions"]
        assert qp["qp_c2_infeasible_policy"] == "strict"
        assert qp["allow_cap_compliance_sells_on_infeasible"] is True
        assert "never admits new buys" in qp["_allow_cap_compliance_sells_on_infeasible_reason"]


def test_qp_live_shadow_telemetry_is_enabled_readonly() -> None:
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        telemetry = cfg["rotation"]["joint_actions"]["qp_live_shadow_telemetry"]
        assert telemetry["enabled"] is True
        assert telemetry["candidate_name"] == "hybrid_option_f_allocator"
        assert telemetry["incumbent_name"] == "current_qp"
        assert telemetry["path"] == "artifacts/live-shadow/qp-live-shadow.jsonl"
        assert "readonly JSONL telemetry only" in telemetry["_reason"]


def test_kelly_sigma_horizon_matches_mu_horizon() -> None:
    """2026-06-11 Kelly horizon-match fix: f*=mu/sigma^2 requires mu and sigma
    on the SAME horizon. mu is the 60d calibrator expected return, so
    sigma_horizon_days must be 60 (was 252/annualized, which inflated variance
    ~4.2x and systematically crushed high-vol names). Prod + golden now carry
    the matched 60d horizon; this replaces the prior 'shadow-only experiment'
    guard that pinned prod to 252 for byte-equivalence."""
    prod = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    golden = load_strategy_config(CONFIG_DIR / "strategy_config.golden.json")
    shadow = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")

    assert prod["ranking"]["kelly_sizing"]["sigma_horizon_days"] == 60
    assert golden["ranking"]["kelly_sizing"]["sigma_horizon_days"] == 60
    # half-Kelly retuned down to 0.3 so the (now correctly larger) targets keep
    # total deployment sane rather than pinning every name at the 12% cap.
    assert prod["ranking"]["kelly_sizing"]["fractional"] == 0.3
    assert golden["ranking"]["kelly_sizing"]["fractional"] == 0.3
    # shadow already ran the matched 60d horizon.
    assert shadow["ranking"]["kelly_sizing"]["sigma_horizon_days"] == 60


def test_soft_exit_min_holding_days_cover_unlisted_regimes() -> None:
    """The sell-side BL-4 follow-up: panel/QP soft-exit horizon guards must
    keep a 60d default in regimes not explicitly listed."""
    for name in ("strategy_config.json", "strategy_config.golden.json"):
        cfg = load_strategy_config(CONFIG_DIR / name)
        panel_days = cfg["risk"]["panel_exit"]["min_holding_days_by_regime"]
        qp_days = cfg["rotation"]["joint_actions"]["qp_soft_sell_guard"][
            "min_holding_days_by_regime"
        ]

        assert panel_days["BULL_CALM"] == 60
        assert panel_days["default"] == 60
        assert qp_days["BULL_CALM"] == 60
        assert qp_days["default"] == 60


def test_core_regime_max_hold_is_far_backstop_in_all_runtime_configs() -> None:
    """Max-hold is a zombie-position backstop, not a per-regime thesis clock."""
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        values = {
            regime: cfg["regime_params"][regime]["max_hold_days"]
            for regime in ("BULL_CALM", "BULL_VOLATILE", "CHOPPY", "BEAR")
        }
        assert values == {
            "BULL_CALM": 500,
            "BULL_VOLATILE": 500,
            "CHOPPY": 500,
            "BEAR": 500,
        }


def test_bear_defensive_sleeve_is_explicit_and_default_off() -> None:
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        sleeve = cfg["bear_defensive_sleeve"]
        assert sleeve["enabled"] is False
        assert "A/B validation" in sleeve["_reason"]
        assert cfg["bear_defensive_slots"] > 0
        assert cfg["bear_defensive_pct"] > 0
        assert cfg["defensive_tickers"]


def test_parking_sleeve_keys_are_explicit_inert_and_shadow_only() -> None:
    """S7 parking-sleeve config companion (renquant-pipeline #157, RS-1 memo):
    the keys exist so the sleeve contract is declared in policy rather than
    living only in the pipeline's safe defaults, but the sleeve stays INERT
    (enabled=false) and SHADOW-only until the RS-1 §4 replay comparison and a
    separately recorded capital authorization. The values below mirror the
    pipeline defaults exactly, so defining them changes nothing. SGOV is
    deliberately NOT a watchlist entry: sleeve-leg price coverage is an
    umbrella follow-up (the daily price fetch is umbrella-owned, and #157's
    shadow tolerates SGOV absence), and the alpha universe / cross-sectional
    admission stats must never include a T-bill ETF."""
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        sleeve = cfg["sleeve"]
        # 2026-07-10: SHADOW logging enabled in prod+golden (JSONL only — no
        # orders, no capital movement; collects the RS-1 SS7 corpus that any
        # future mode=live decision is gated on). shadow.json (arm S-0.5,
        # single-delta contract) stays inert. mode=live remains gated on the
        # RS-1 §4 replay comparison + recorded capital authorization.
        expected_sleeve = name != "strategy_config.shadow.json"
        assert sleeve["enabled"] is expected_sleeve, (
            f"{name}: sleeve shadow-logging contract 2026-07-10"
        )
        assert sleeve["mode"] == "shadow", f"{name}: only shadow mode may be enabled"
        assert sleeve["spy_symbol"] == "SPY"
        assert sleeve["sgov_symbol"] == "SGOV"
        assert sleeve["reserve_pv_pct"] == 0.05
        assert sleeve["beta_max"] == 0.6
        assert sleeve["beta_pos"] == 1.0
        assert sleeve["min_trade_notional"] == 50.0
        assert sleeve["dd_budget_pct"] == 0.15
        assert sleeve["log_path"] == "logs/parking_sleeve_shadow.jsonl"
        assert "RS-1" in sleeve["_comment"], f"{name}: sleeve must cite RS-1 lineage"
        # SPY leg is already priced via the watchlist; SGOV coverage is the
        # umbrella follow-up, NOT an alpha-universe entry.
        assert sleeve["spy_symbol"] in cfg["watchlist"]
        assert sleeve["sgov_symbol"] not in cfg["watchlist"]


def test_intraday_decisioning_keys_match_scheduler_defaults_and_stay_shadow_only() -> None:
    """renquant105 Stage-1 SHADOW arming (RFC #208 §8.3/§10; consumer:
    renquant-orchestrator #266 ``intraday_session_scheduler.load_intraday_config``;
    #266 landing-checklist step 3, config half).

    Every value below mirrors the scheduler's safe defaults exactly, so
    defining the keys changes no scheduler behavior — the section's one real
    bit is ``enabled=true``, which is ONE of three independent gates: the
    scheduler is a SEPARATE launchd-run process (nothing in the daily run
    invokes it) and also requires the env kill switch
    ``RENQUANT_INTRADAY_DECISIONING`` truthy AND the kill-switch file absent,
    both machine-side ask-first landing steps. Until that install, this
    config is inert.

    THE STAGE-2 BAR, MECHANICALLY: ``mode`` must be ``"shadow"``. #266
    runtime-asserts never-submit on every tick and structurally downgrades
    ``mode="live"`` to shadow (§9.3a) — but authorizing live is a policy
    decision that must be VISIBLE, so this pin makes any flip to "live" fail
    the suite until the Stage-2 authorization deliberately rewrites this
    test alongside the config."""
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        intraday = cfg["intraday_decisioning"]
        # The one real bit: config gate armed (inert without the machine-side
        # env flag + launchd install; see the section _comment).
        assert intraday["enabled"] is True, f"{name}: Stage-1 shadow arming"
        # The Stage-2 authorization bar: shadow-only, pinned.
        assert intraday["mode"] == "shadow", (
            f"{name}: mode='live' is a Stage-2 authorization (RFC #208 §9.3a) "
            "— rewrite this pin ONLY alongside that recorded decision"
        )
        # Scheduler defaults (§5/§11b), mirrored exactly.
        assert intraday["tick_seconds"] == 720
        assert intraday["entry_open_delay_seconds"] == 300
        assert intraday["entry_close_cutoff_seconds"] == 1800
        assert intraday["canary_allowlist"] == []
        # null => the scheduler's default kill-switch path
        # (<data_root>/data/rq105/intraday_decisioning.KILL).
        assert intraday["kill_switch_file"] is None
        assert "#208" in intraday["_comment"], f"{name}: must cite RFC #208"
        assert "#266" in intraday["_comment"], f"{name}: must cite orchestrator #266"
        # No stray keys: the scheduler reads exactly this set (fail-closed on
        # malformed values); a typo'd extra key would silently do nothing.
        assert set(intraday) == {
            "enabled",
            "mode",
            "tick_seconds",
            "entry_open_delay_seconds",
            "entry_close_cutoff_seconds",
            "canary_allowlist",
            "kill_switch_file",
            "_comment",
        }, f"{name}: unexpected intraday_decisioning keys"


def test_fingerprint_accept_legacy_stamps_is_explicit_and_true() -> None:
    """M6 stage-2 step 1, config half (renquant-orchestrator
    ``doc/design/2026-07-03-m6-stage2-fingerprint-migration.md`` §3 step 1;
    reader: renquant-pipeline #164
    ``fingerprint_dispatch.accept_legacy_stamps``, absent => true).

    Explicit ``true`` equals the reader's default, so merging this changes
    NOTHING running today. The point is declaring the migration window
    (version-dispatched fingerprint verification accepts legacy versionless
    stamps alongside schema-v1 at both fail-closed checks:
    ``_assert_calibrator_matches_scorer`` and
    ``_assert_calibrator_matches_entry``) in POLICY, so the future flip is a
    reviewable strategy-config PR instead of a silent code-default change.

    THE STEP-4 BAR, MECHANICALLY: flipping to ``false`` (v1-only — a
    versionless stamp then fails closed with the re-stamp-under-v1 remedy) is
    the deliberate stage-2 STEP-4 migration act, gated on the step-3 census
    running green over the full observation window (design §3 steps 3-4).
    This pin makes any flip fail this repo's suite until the step-4 decision
    deliberately rewrites the test alongside the config — mirroring the
    intraday ``mode == "shadow"`` pin (PR #41) and the sleeve inertness pin
    (PR #39)."""
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        fingerprint = cfg["ranking"]["panel_scoring"]["fingerprint"]
        assert fingerprint["accept_legacy_stamps"] is True, (
            f"{name}: accept_legacy_stamps=false is the M6 stage-2 STEP-4 "
            "migration act (v1-only verification; design §3 step 4) — rewrite "
            "this pin ONLY alongside that recorded decision, after the step-3 "
            "census is green"
        )
        comment = fingerprint["_comment"]
        assert "#164" in comment, f"{name}: must cite pipeline #164 (the reader)"
        assert "2026-07-03-m6-stage2-fingerprint-migration" in comment, (
            f"{name}: must cite the M6 stage-2 design doc"
        )
        # Exactly the key #164's reader consumes (+ provenance): a typo'd
        # extra key under this section would silently do nothing.
        assert set(fingerprint) == {"accept_legacy_stamps", "_comment"}, (
            f"{name}: unexpected fingerprint keys"
        )


# D6-§2a two-arm shadow A/B — the BINDING contract for the arm configs.
# doc/design/2026-07-09-governor-prereg-replay-protocol.md §2a on
# renquant-orchestrator main; the commit below is #443's merge commit.
SHADOW_AB_PROTOCOL_DOC = "doc/design/2026-07-09-governor-prereg-replay-protocol.md"
SHADOW_AB_PROTOCOL_COMMIT = "8981edfa2a2ef71f538bac5b965bc389f21a9eb7"
SHADOW_AB_TREATMENT_KEY = "ranking.panel_scoring.buy_floor_std_mult"
SHADOW_AB_ARM_ANNOTATION_KEY = "ranking.panel_scoring._arm"


def _diff_paths(a, b, prefix: str = "") -> set[str]:
    """Dotted paths at which two parsed JSON trees differ (missing keys count)."""
    if isinstance(a, dict) and isinstance(b, dict):
        paths: set[str] = set()
        for key in set(a) | set(b):
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in a or key not in b:
                paths.add(child)
            else:
                paths |= _diff_paths(a[key], b[key], child)
        return paths
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        paths = set()
        for i, (va, vb) in enumerate(zip(a, b)):
            paths |= _diff_paths(va, vb, f"{prefix}[{i}]")
        return paths
    if type(a) is type(b) and a == b:
        return set()
    # bool is an int subclass; JSON 1 vs 1.0 vs true must not silently equate.
    if isinstance(a, bool) != isinstance(b, bool):
        return {prefix}
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a == b:
        return set()
    return {prefix} if a != b else set()


def test_shadow_ab_arm_configs_carry_frozen_2a_values() -> None:
    """D6-§2a two-arm shadow A/B — frozen NORMATIVE arm values (orchestrator
    #443 merged; §2a, 'Corrected design — two simultaneous isolated shadow
    arms, identical except the floor').

    Arm S-0.5 (TREATMENT)  = strategy_config.shadow_a.json, tag alpaca_shadow_a
    Arm S-1.0 (CONTROL)    = strategy_config.shadow_b.json, tag alpaca_shadow_b

    Both arms live in DEDICATED files, never the legacy strategy_config.
    shadow.json (Step-4 ops shadow, broker tag alpaca_shadow) — a Codex
    review on #53 caught an earlier draft mutating shadow.json in place,
    which would have silently re-armed the legacy single-arm shadow with
    the treatment before P-2 isolates the two new arms. See
    test_legacy_shadow_config_untouched_by_shadow_ab below.

    Both arms: scorer hf_patchtst, Kelly fractional 0.5 / max_concentration
    0.35, BULL_CALM max_position_pct 0.15, one_share_floor_enabled true,
    buy_floor adaptive_mean_std. The ONE functional delta is
    buy_floor_std_mult: 0.5 (treatment) vs 1 (control, production's floor
    multiple). The broker-state tags are threaded by the P-2 orchestrator
    two-arm runner (orchestrator #451), NOT by config keys — the r5 draft's
    second config key (live.preflight.strict shim) is WITHDRAWN in §2a, so
    NO 'live' section may appear in either arm. Rewrite these pins ONLY under
    a new protocol version: §2a's treatment-fingerprint drift rule VOIDS the
    running experiment if either arm's resolved config hash changes mid-run."""
    arm_a = load_strategy_config(CONFIG_DIR / "strategy_config.shadow_a.json")
    arm_b = load_strategy_config(CONFIG_DIR / "strategy_config.shadow_b.json")

    for name, cfg in (("shadow_a", arm_a), ("shadow_b", arm_b)):
        panel = cfg["ranking"]["panel_scoring"]
        assert panel["kind"] == "hf_patchtst", f"{name}: §2a frozen scorer"
        assert panel["buy_floor"] == "adaptive_mean_std", (
            f"{name}: §2a freezes buy_floor=adaptive_mean_std in BOTH arms"
        )
        assert cfg["ranking"]["kelly_sizing"]["fractional"] == 0.5, name
        assert cfg["ranking"]["kelly_sizing"]["max_concentration"] == 0.35, name
        assert cfg["regime_params"]["BULL_CALM"]["max_position_pct"] == 0.15, name
        assert cfg["sizing"]["one_share_floor_enabled"] is True, name
        # Withdrawn r5 preflight shim must NOT come back as a config key:
        # arm-symmetric preflight policy is P-2-owned (§2a execution plan).
        assert "live" not in cfg, (
            f"{name}: the live.preflight.strict shim is WITHDRAWN by §2a"
        )
        # Provenance: the arm files must cite the merged protocol + commit.
        reason = panel["_buy_floor_reason"]
        assert SHADOW_AB_PROTOCOL_DOC in reason, name
        assert SHADOW_AB_PROTOCOL_COMMIT in reason, name

    assert arm_a["ranking"]["panel_scoring"]["buy_floor_std_mult"] == 0.5
    assert arm_b["ranking"]["panel_scoring"]["buy_floor_std_mult"] == 1

    # Arm identity annotations carry the frozen §2a broker-state tags
    # (runner-threaded; deliberately NOT functional config keys).
    arm_a_note = arm_a["ranking"]["panel_scoring"]["_arm"]
    arm_b_note = arm_b["ranking"]["panel_scoring"]["_arm"]
    assert "S-0.5 TREATMENT" in arm_a_note
    assert "alpaca_shadow_a" in arm_a_note
    assert "S-1.0 CONTROL" in arm_b_note
    assert "alpaca_shadow_b" in arm_b_note


def test_shadow_ab_arms_differ_in_exactly_the_treatment_key() -> None:
    """§2a config-drift pin, enforced LITERALLY: shadow_b is 'a clone of
    shadow_a.json differing in exactly ONE functional key (plus inert
    `_reason` annotation strings)'. Three independent enforcements: (1)
    line-level — the two files have identical line counts and differ on
    exactly the buy_floor_std_mult line and the _arm annotation line; (2)
    tree-level — the parsed-JSON diff is exactly those two dotted paths;
    (3) byte-level — with those two paths removed, the canonical
    serializations are byte-equal."""
    a_text = (CONFIG_DIR / "strategy_config.shadow_a.json").read_text()
    b_text = (CONFIG_DIR / "strategy_config.shadow_b.json").read_text()

    # (1) line-level: same shape, exactly two differing lines, on known keys.
    a_lines = a_text.splitlines()
    b_lines = b_text.splitlines()
    assert len(a_lines) == len(b_lines), "arm files must be line-for-line clones"
    differing = [
        (la, lb) for la, lb in zip(a_lines, b_lines) if la != lb
    ]
    differing_keys = sorted(
        la.strip().split(":")[0].strip().strip('"') for la, _ in differing
    )
    assert differing_keys == ["_arm", "buy_floor_std_mult"], (
        f"arm files may differ ONLY on the treatment key and the _arm "
        f"annotation; got differing lines for {differing_keys}"
    )

    # (2) tree-level: the full recursive diff is exactly the two paths.
    arm_a = json.loads(a_text)
    arm_b = json.loads(b_text)
    assert _diff_paths(arm_a, arm_b) == {
        SHADOW_AB_TREATMENT_KEY,
        SHADOW_AB_ARM_ANNOTATION_KEY,
    }

    # (3) byte-level: everything else is byte-equal under canonical dump.
    for cfg in (arm_a, arm_b):
        panel = cfg["ranking"]["panel_scoring"]
        del panel["buy_floor_std_mult"]
        del panel["_arm"]
    assert json.dumps(arm_a, sort_keys=True) == json.dumps(arm_b, sort_keys=True)


def test_shadow_ab_leaves_prod_and_golden_at_production_baseline() -> None:
    """§2a prerequisite-PR contract: the config-only treatment PR verifies
    'prod/golden untouched'. Pin the production baseline on every §2a-relevant
    key so the shadow A/B cannot leak into the live book: the production
    buy-floor stays adaptive_mean_std at 1.0σ (XGB primary), sizing stays at
    the production Kelly 0.3/0.12, BULL_CALM 0.12, one-share floor OFF. Live
    enablement of the 0.5σ treatment is a SEPARATE future PR carrying the §2a
    Tier-2 verdict memo + pre-registration gate + Codex review (§2a decision
    rule) — never this pin silently drifting."""
    for name in ("strategy_config.json", "strategy_config.golden.json"):
        cfg = load_strategy_config(CONFIG_DIR / name)
        panel = cfg["ranking"]["panel_scoring"]
        assert panel["kind"] == "xgb", f"{name}: production primary stays XGB"
        assert panel["buy_floor"] == "adaptive_mean_std", name
        assert panel["buy_floor_std_mult"] == 1, (
            f"{name}: production floor multiple stays 1.0σ — flipping it is a "
            "live-book behavior change requiring the §2a verdict memo + "
            "pre-registration gate + Codex review in its own PR"
        )
        assert cfg["ranking"]["kelly_sizing"]["fractional"] == 0.3, name
        assert cfg["ranking"]["kelly_sizing"]["max_concentration"] == 0.12, name
        assert cfg["regime_params"]["BULL_CALM"]["max_position_pct"] == 0.12, name
        assert cfg["sizing"]["one_share_floor_enabled"] is False, name


def test_legacy_shadow_config_untouched_by_shadow_ab() -> None:
    """Codex review on #53: an earlier draft of this PR mutated
    strategy_config.shadow.json IN PLACE to the 0.5σ treatment values. That
    file is the LEGACY Step-4 ops shadow config (broker tag alpaca_shadow,
    still invoked daily by daily_104.sh independent of the D6-§2a
    experiment). Mutating it would have silently re-armed the legacy
    single-arm shadow with an uncontrolled treatment observation before
    P-2 isolates the two new arms (alpaca_shadow_a/_b) — contaminating the
    paired experiment. Pin the legacy file at its PRE-experiment values:
    adaptive_quantile / std_mult 1 (the 2026-06-11 false-BEAR audit
    values), with no _arm annotation and no reference to the D6-§2a
    protocol anywhere in it. The two-arm experiment lives ENTIRELY in
    strategy_config.shadow_a.json / strategy_config.shadow_b.json."""
    legacy = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")
    panel = legacy["ranking"]["panel_scoring"]
    assert panel["buy_floor"] == "adaptive_quantile", (
        "legacy shadow.json must stay at its pre-#53 adaptive_quantile "
        "value — the D6-§2a treatment must never leak into the legacy "
        "Step-4 ops shadow path"
    )
    assert panel["buy_floor_std_mult"] == 1, (
        "legacy shadow.json must stay at its pre-#53 std_mult=1 value"
    )
    assert "_arm" not in panel, (
        "legacy shadow.json must carry no D6-§2a arm annotation — it is "
        "not part of the two-arm experiment"
    )
    reason = panel.get("_buy_floor_reason", "")
    assert SHADOW_AB_PROTOCOL_DOC not in reason, (
        "legacy shadow.json must not cite the §2a protocol — it is not "
        "one of the experiment's arms"
    )


def test_strategy_repo_has_no_generated_experiment_configs() -> None:
    generated = sorted(
        p.name for p in CONFIG_DIR.glob("strategy_config.*.json")
        if ".sim_" in p.name or ".codex_" in p.name or ".whatif_" in p.name
    )
    assert generated == []


def test_strategy_package_loads_and_fingerprints_active_config() -> None:
    cfg_path = CONFIG_DIR / "strategy_config.json"
    cfg = load_strategy_config(cfg_path)
    manifest = strategy_manifest(cfg_path)

    assert cfg["watchlist"]
    assert manifest["strategy"] == "renquant_104"
    assert manifest["fingerprint"].startswith("sha256:")
    assert manifest["watchlist_size"] == len(cfg["watchlist"])


def test_readme_records_latest_production_sync_source() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert LATEST_PRODUCTION_SYNC_SOURCE in readme


def test_loader_rejects_duplicate_watchlist_and_missing_sector(tmp_path: Path) -> None:
    cfg = _load("strategy_config.json")
    cfg["watchlist"] = ["AAPL", "AAPL", "MSFT"]
    cfg["sector_map"] = {"AAPL": "Technology"}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate tickers"):
        load_strategy_config(path)


def test_loader_rejects_local_absolute_artifact_path(tmp_path: Path) -> None:
    cfg = _load("strategy_config.json")
    cfg["ranking"]["panel_scoring"]["artifact_path"] = "/Users/renhao/model.json"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")

    with pytest.raises(ValueError, match="repo-relative"):
        load_strategy_config(path)


def test_shadow_blend_profile_semantic_pins() -> None:
    """Pin the shadow_blend lane profile (umbrella#535 Step 5 / pipeline#218
    kind=blend) so its identity pins and its calibration/mu decision cannot
    silently drift.

    The profile is strategy_config.json + EXACTLY six deltas:
      1. kind="blend" + two pinned components (0=prod scorer, 1=top-decile clf)
         with BOTH identity pins each (content abbrev-16, fp verbatim —
         pipeline#218 fail-closed pin semantics);
      2. global_calibration DISABLED (the prod calibrator binds the prod scorer
         fp; against the blend composite fp it would config_mismatch fail-close
         — the 2026-06 shadow-config-FP-restamp trap);
      3. conviction_gate DISABLED (floors on calibrator expected_return, which
         no longer exists — every candidate would drop as conviction:mu_nan);
      4. ranking.kelly_sizing DISABLED (use_calibrator_mu would zero every
         target — legacy multiplicative sizing sizes the shadow intents);
      5. shadow_models/shadow_experiment removed (this lane IS the blend);
      6. every absolute probability-domain threshold nulled/disabled
         (buy_floor, panel_veto, rotation floors, qp_admission_gate rank/ER
         floors) — the lane's rank_score is a raw z-composite and the
         2026-08-02 pipeline domain guard fail-closes probability floors on
         uncalibrated scores; admission is ordinal-only.
    Everything else must stay semantically identical to production so the
    lane remains "shadow like prod minus submission".
    """
    prod = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    blend = load_strategy_config(CONFIG_DIR / "strategy_config.shadow_blend.json")
    panel = blend["ranking"]["panel_scoring"]

    # 1. blend kind + exact component pins (order-significant: 0=prod, 1=clf).
    assert panel["enabled"] is True
    assert panel["kind"] == "blend"
    assert panel["artifact_path"] == "artifacts/prod/panel-ltr.alpha158_fund.json"
    components = panel["components"]
    assert [
        {
            "artifact_path": c["artifact_path"],
            "expected_content_sha256": c["expected_content_sha256"],
            "expected_config_fingerprint": c["expected_config_fingerprint"],
        }
        for c in components
    ] == [
        {
            "artifact_path": "artifacts/prod/panel-ltr.alpha158_fund.json",
            "expected_content_sha256": "sha256:6461b827ab2339a8",  # rotated 2026-08-04: RFC#210 promotion swapped the prod component (was 04d7a381, June-trained)
            "expected_config_fingerprint": "sha256:f8fb2259b2bf1537",
        },
        {
            "artifact_path": "artifacts/shadow/panel-clf.top-decile.fwd60.json",
            "expected_content_sha256": "sha256:1e644354e0981f47",
            "expected_config_fingerprint": (
                "sha256:1d8f167fed18cd8cb1e0760251fdd5398724e630462d92b41561d"
                "2e19973e41b"
            ),
        },
    ]
    # Component 0 must be the SAME artifact the production primary runs —
    # the blend is z(prod)+z(clf), not a new prod model.
    assert (
        components[0]["artifact_path"]
        == prod["ranking"]["panel_scoring"]["artifact_path"]
    )
    # Both clf pins must match the prod config's shadow_models clf leg
    # (single source of the 2026-07-27 re-stamp identity).
    clf_leg = next(
        m
        for m in prod["ranking"]["panel_scoring"]["shadow_models"]
        if m["name"] == "topdecile_clf_blend_leg"
    )
    assert components[1]["expected_content_sha256"] == clf_leg["expected_content_sha256"]
    assert (
        components[1]["expected_config_fingerprint"]
        == clf_leg["expected_config_fingerprint"]
    )

    # 2-4. the calibration/mu decision, pinned.
    assert panel["global_calibration"]["enabled"] is False
    assert panel["conviction_gate"]["enabled"] is False
    assert blend["ranking"]["kelly_sizing"]["enabled"] is False
    # QP mu contract stays strict and alpha_to_mu stays the legal mu source.
    assert blend["rotation"]["joint_actions"]["qp_mu_contract"] == "strict"
    assert blend["ranking"]["alpha_to_mu"]["enabled"] is True

    # 5. no shadow legs on the blend lane.
    assert "shadow_models" not in panel
    assert "shadow_experiment" not in panel

    # 6. wash_sale_min_material_npv is an INTENTIONAL shadow-only delta.
    #
    # The materiality floor is lit at 1.00 on every shadow profile and left UNSET on
    # live and golden, where the pipeline resolver falls back to
    # WASH_SALE_MIN_MATERIAL_NPV_LEGACY = 0.0. That asymmetry is the point of the
    # de-scope on strategy#73: the shadow lanes run the same selection path and place
    # no orders, so they generate the multi-session released-block evidence that a
    # live activation would need, while live keeps its existing behaviour.
    #
    # Named here rather than normalised silently: this contract exists to make every
    # blend-vs-prod difference deliberate, and an unlisted delta that merely happens
    # to be popped is indistinguishable from one nobody noticed.
    assert blend["wash_sale_min_material_npv"] == 1.00
    # 2026-08-03: prod's floor went LIVE at the operator's $5 (was ABSENT —
    # shadow-only de-scope). The blend lane deliberately keeps the stricter
    # $1 evidence floor; the delta is now value-vs-value, still declared.
    assert prod["wash_sale_min_material_npv"] == 5.00

    # 6. raw-z-domain coherence (2026-08-03). The 2026-08-02 pipeline pin
    # deployed the rank_score domain guard: any buy_floor mode fail-closes when
    # calibration did not run (rank_score_domain_uncalibrated — it emptied 87
    # candidates on 2026-08-03 and flipped the lane STRUCTURAL_BLOCK). This
    # lane is uncalibrated BY DESIGN (delta 2), so every absolute
    # probability-domain threshold is nulled/disabled and admission is
    # ordinal-only (top_n, slots, risk gates). Pin each one so a merge-back
    # from prod cannot silently re-arm a fail-close.
    assert blend["ranking"]["panel_scoring"]["buy_floor"] is None
    assert blend["model_sell"]["panel_veto"]["enabled"] is False
    assert blend["rotation"]["panel_buy_floor"] is None
    assert blend["rotation"]["panel_sell_floor"] is None
    assert blend["rotation"]["panel_buy_rank_floor"] is None
    gate = blend["rotation"]["joint_actions"]["qp_admission_gate"]
    assert gate["min_rank_score"] is None
    assert gate["topup_min_rank_score"] is None
    # A missing calibrator ER is a REFUSAL on the current pin
    # (qp_admission_expected_return), so the map must be null here.
    assert gate["min_expected_return_by_regime"] is None

    # Everything else: semantically identical to production (the profile is
    # "prod minus submission", not a fork). Normalize away the declared deltas
    # + provenance notes, then require equality.
    prod_norm = _strip_provenance(prod)
    blend_norm = _strip_provenance(blend)
    for cfg in (prod_norm, blend_norm):
        p = cfg["ranking"]["panel_scoring"]
        p.pop("kind", None)
        p.pop("components", None)
        p.pop("shadow_models", None)
        p.pop("shadow_experiment", None)
        p.pop("buy_floor", None)
        p["global_calibration"].pop("enabled", None)
        p["conviction_gate"].pop("enabled", None)
        cfg["ranking"]["kelly_sizing"].pop("enabled", None)
        cfg.pop("wash_sale_min_material_npv", None)
        cfg["model_sell"]["panel_veto"].pop("enabled", None)
        cfg["rotation"].pop("panel_buy_floor", None)
        cfg["rotation"].pop("panel_sell_floor", None)
        cfg["rotation"].pop("panel_buy_rank_floor", None)
        qp_gate = cfg["rotation"]["joint_actions"]["qp_admission_gate"]
        qp_gate.pop("min_rank_score", None)
        qp_gate.pop("topup_min_rank_score", None)
        qp_gate.pop("min_expected_return_by_regime", None)
    assert blend_norm == prod_norm


def _strip_provenance(value):
    if isinstance(value, dict):
        return {
            k: _strip_provenance(v)
            for k, v in value.items()
            if not str(k).startswith("_")
        }
    if isinstance(value, list):
        return [_strip_provenance(v) for v in value]
    return value


# --- wash-sale materiality floor: SHADOW-only until it earns live (strategy#73) ---
#
# renquant-pipeline resolves this key with WASH_SALE_MIN_MATERIAL_NPV_LEGACY = 0.0
# when it is absent, and its own docstring says "this repo never substitutes a policy
# value of its own". So UNSET is not an oversight here — it is the live gate keeping
# pre-existing behaviour while the shadow lanes generate the evidence a live
# activation would need.

SHADOW_PROFILES = (
    "strategy_config.shadow.json",
    "strategy_config.shadow_a.json",
    "strategy_config.shadow_b.json",
    "strategy_config.shadow_blend.json",
    "strategy_config.shadow_momentum.json",
)
LIVE_PROFILES = ("strategy_config.json", "strategy_config.golden.json")
WASH_SALE_FLOOR_KEY = "wash_sale_min_material_npv"


def test_every_shadow_profile_lights_the_wash_sale_floor() -> None:
    """All four, not "the ones I remembered" — a floor lit on three of four lanes
    produces evidence that does not describe the fourth."""
    for name in SHADOW_PROFILES:
        cfg = _load(name)
        assert cfg.get(WASH_SALE_FLOOR_KEY) == 1.00, (
            f"{name} does not carry the shadow materiality floor")


def test_live_floor_is_the_operator_decision_and_golden_stays_unset() -> None:
    """The deliberate reversal this test's previous form demanded.

    2026-08-03, operator, verbatim: 「低于 $5 放行」 — given in direct response
    to "wash sale不能全部杀死，要科学地看成本分析". The promotion criteria the
    shadow de-scope named are met: the mechanism is merged and A/B
    byte-invariance-proven at floor 0 (pipeline#251), the shadow lanes ran the
    $1.00 floor and measured real per-block NPV costs ($0.04-$0.99), and the
    07-28 incident quantified the harm of the binary rule (~$15 of tax
    protected while $6.8k idled across 3 of 5 sessions). LIVE pins to exactly
    5.00 — a different value is a NEW operator decision, not a tweak. GOLDEN
    moves in lockstep: it is the daily drift REFERENCE for the live config
    (test_live_and_golden_agree_about_the_floor), so the pair must carry the
    same value or the drift WARN fires every run.
    """
    live = _load("strategy_config.json")
    assert live.get(WASH_SALE_FLOOR_KEY) == 5.00
    golden = _load("strategy_config.golden.json")
    assert golden.get(WASH_SALE_FLOOR_KEY) == 5.00

def test_live_and_golden_agree_about_the_floor() -> None:
    """`scripts/daily_104.sh` uses golden as the drift reference for the live config,
    so lighting the floor in one and not the other fires the drift WARN every run.
    They must move together in either direction."""
    live, golden = _load("strategy_config.json"), _load("strategy_config.golden.json")
    assert (WASH_SALE_FLOOR_KEY in live) == (WASH_SALE_FLOOR_KEY in golden)
    assert live.get(WASH_SALE_FLOOR_KEY) == golden.get(WASH_SALE_FLOOR_KEY)


# --- momentum shadow lane (GOAL-7 slice 4): PENDING the slice-5 grant batch ---
#
# The momentum entry's artifact_path points at the weekly TRAIN job's
# append-only artifact ledger (the orch#757 publish set; serving-path
# convention fixed by model#197). Until the grant batch installs the job and
# the first artifact + ledger are published, that path does NOT resolve
# anywhere — which is exactly why the slice-4 config PR merges only inside the
# batch (order: job installed -> first artifact published -> config merged ->
# pin advance). No test here resolves the path against the operator's disk
# (the static resolve gate is umbrella CI at pin-advance time; a disk-reading
# test in this repo would be red or vacuously green per machine). Instead this
# named set BOUNDS the declared pending state to exactly the entries that
# carry it — the launchd-manifest PENDING_INSTALL idiom: a second pending
# entry cannot ride in unnamed, and the post-batch follow-up PR that deletes
# the _2026_08_02_pending_first_artifact key must shrink this set in the same
# change. 2026-08-02: the batch LANDED (first artifact + genesis ledger row
# published, entry merged in #77, pin advanced in RenQuant#555) and the
# momentum key was deleted with this shrink — the set is EMPTY until a future
# lane declares a pending state by name.
#
# 2026-08-03: the FAST momentum lane (renquant-model#199 item 3) is exactly
# that future lane. Its ledger (artifacts/momentum_fast/...) is written by the
# SAME weekly job's new second, non-fatal train step (#199 item 2) — nothing
# publishes it until that wrapper change is deployed AND a Saturday firing
# runs the fast lane, so the entry declares the pending state by name. While
# pending, the daily shadow record for the lane is the unresolved-artifact
# NOT-LOADED record (artifact_resolved false — pipeline shadow_scoring's
# missing-file path), NOT the not_yet_published expected skip (that skip
# requires an existing chain-verified zero-row ledger). The post-first-publish
# follow-up PR deletes the entry's _2026_08_03_pending_first_artifact key and
# shrinks this set back to empty in the same change (the v0/#78 precedent).
PENDING_FIRST_ARTIFACT: set[str] = {"momentum_fast_v1_shadow"}
MOMENTUM_SHADOW_LEDGER_PATH = "artifacts/momentum/momentum_artifact_ledger.jsonl"
FAST_MOMENTUM_SHADOW_LEDGER_PATH = (
    "artifacts/momentum_fast/momentum_artifact_ledger.jsonl")


def test_pending_first_artifact_guard_names_exactly_the_momentum_entry() -> None:
    for name in LIVE_PROFILES:
        panel = _load(name)["ranking"]["panel_scoring"]
        pending = {
            m["name"]
            for m in panel.get("shadow_models") or []
            if any(str(k).endswith("_pending_first_artifact") for k in m)
        }
        assert pending == PENDING_FIRST_ARTIFACT, (
            f"{name}: shadow entries declaring a pending-first-artifact state "
            f"{sorted(pending)} != the bounded named set "
            f"{sorted(PENDING_FIRST_ARTIFACT)} — either an unnamed pending "
            f"entry rode in, or the grant batch landed and the pending key "
            f"must be deleted together with this set"
        )


def test_momentum_shadow_entries_pin_their_ledger_paths_with_no_repo_escape() -> None:
    """The `../../` incident class, asserted at the source: each momentum
    lane's artifact_path is repo-relative (canonical resolver:
    strategy_dir-first, same base the blend leg resolves under), contains no
    `..` escape, and the two lanes pin DISTINCT sibling directories — a fast
    entry reusing the slow ledger would make the serving loader alternate
    lanes off one tail (model#199 item 3)."""
    lanes = {
        "momentum_residual_v0_shadow": MOMENTUM_SHADOW_LEDGER_PATH,
        "momentum_fast_v1_shadow": FAST_MOMENTUM_SHADOW_LEDGER_PATH,
    }
    for name in LIVE_PROFILES:
        panel = _load(name)["ranking"]["panel_scoring"]
        for lane_name, ledger_path in lanes.items():
            matches = [
                m
                for m in panel.get("shadow_models") or []
                if m.get("name") == lane_name
            ]
            assert len(matches) == 1, f"{name}: {lane_name} entry missing"
            entry = matches[0]
            assert entry["kind"] == "momentum_residual"
            assert entry["artifact_path"] == ledger_path
            p = Path(entry["artifact_path"])
            assert not p.is_absolute()
            assert ".." not in p.parts
    assert MOMENTUM_SHADOW_LEDGER_PATH != FAST_MOMENTUM_SHADOW_LEDGER_PATH
    assert (Path(FAST_MOMENTUM_SHADOW_LEDGER_PATH).parent
            != Path(MOMENTUM_SHADOW_LEDGER_PATH).parent)


def test_shadow_momentum_profile_semantic_pins() -> None:
    """Pin the shadow_momentum lane profile (pipeline#259 primary surface;
    operator directive: show the momentum model's orders).

    The profile is strategy_config.shadow_blend.json + EXACTLY six deltas:
      1. kind="momentum_residual" + artifact_path = the lane's machine-produced
         digest-chained ledger (the serving loader follows the verified tail
         row to the dated artifact);
      2. expected_config_fingerprint = the artifact's own params stamp —
         pipeline#259's kind-aware consistency check fail-closes on an
         absent/mismatched/non-string pin AND on an unstamped artifact, so
         this pin is load-bearing, not documentation;
      3. no components (single lookup scorer; the blend's two-leg pin block
         does not apply);
      4. realized-vol EXCLUSION disabled (2026-08-03, operator directive: the
         flat 60% cap decapitated the signal — the model's top-10 was 9/10
         semis, all vol-gated, leaving ranks 13-16 as the slate). Risk moves
         to sigma-scaled SIZING + the per-name/sector caps, which stay ON;
      5. the foreign-ER conjunct disabled (alpha_to_mu vetoed ranks 14-16) —
         the lane's own direction gate, positive momentum z, stays ON;
      6. wash_sale_days=0 (a hypothetical lane pays no tax; binary blocks
         removed the model's ranks 11-12 on 'P/L unknown'). The LIVE lane's
         filter is untouched.
    Everything else — including every delta-6 raw-domain null, which applies
    identically because momentum scores are uncalibrated z's — must stay
    semantically identical to the blend profile, which is itself pinned
    against production above. DORMANT until a reviewed daily step consumes
    it (rehearsed e2e 2026-08-03: 84/84 scored, ECONOMIC_TRADE).
    """
    blend = load_strategy_config(CONFIG_DIR / "strategy_config.shadow_blend.json")
    mom = load_strategy_config(CONFIG_DIR / "strategy_config.shadow_momentum.json")
    panel = mom["ranking"]["panel_scoring"]

    # 1-3. the declared deltas, exact.
    assert panel["kind"] == "momentum_residual"
    assert panel["artifact_path"] == (
        "artifacts/momentum/momentum_artifact_ledger.jsonl")
    assert panel["expected_config_fingerprint"] == "momentum-v0-fd65161a20b29314"
    assert "components" not in panel

    # 4-6. the lane-risk deltas, exact.
    assert mom["risk_gates"]["realized_vol"]["enabled"] is False
    assert panel["require_positive_expected_return_for_buy"] is False
    assert panel.get("require_positive_raw_signal_for_buy") is None  # default ON
    assert mom["wash_sale_days"] == 0

    # The raw-domain coherence set carries over verbatim (delta 6 of the blend
    # profile — same reason: uncalibrated scores, no probability thresholds).
    assert panel["buy_floor"] is None
    assert mom["model_sell"]["panel_veto"]["enabled"] is False
    assert mom["rotation"]["joint_actions"]["qp_admission_gate"][
        "min_expected_return_by_regime"] is None

    # Everything else: semantically identical to the blend profile.
    blend_norm = _strip_provenance(blend)
    mom_norm = _strip_provenance(mom)
    for cfg in (blend_norm, mom_norm):
        p = cfg["ranking"]["panel_scoring"]
        p.pop("kind", None)
        p.pop("components", None)
        p.pop("artifact_path", None)
        p.pop("expected_config_fingerprint", None)
        p.pop("require_positive_expected_return_for_buy", None)
        cfg.pop("risk_gates", None)
        cfg.pop("wash_sale_days", None)
    assert mom_norm == blend_norm


def test_shadow_blend_momentum_profile_semantic_pins() -> None:
    """GOAL-8 S1 lane profile (prereg FROZEN in renquant-orchestrator
    doc/research/2026-08-04-goal8-s1-zblend-prereg.md; consumed by
    daily_104.sh Step 5b): the shadow_blend construction with EXACTLY one
    difference — component 1 is the SLOW momentum ledger-pointer leg
    (pipeline#261 kind dispatch) instead of the top-decile clf.

    Same six deltas vs production as test_shadow_blend_profile_semantic_pins;
    everything else identical. The momentum leg's identity contract differs
    BY DESIGN: NO expected_content_sha256 (append-only ledger — a byte pin
    is stale by design; pipeline#261 REFUSES one), and
    expected_config_fingerprint pins the RECIPE (the loader-stamped params
    fingerprint, measured 2026-08-04 from the live genesis ledger tail)."""
    prod = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    blend = load_strategy_config(
        CONFIG_DIR / "strategy_config.shadow_blend.json")
    mom = load_strategy_config(
        CONFIG_DIR / "strategy_config.shadow_blend_momentum.json")
    panel = mom["ranking"]["panel_scoring"]

    # 1. blend kind; component 0 = the EXACT prod leg the clf blend pins;
    #    component 1 = the momentum ledger pointer, recipe-pinned, no byte pin.
    assert panel["enabled"] is True
    assert panel["kind"] == "blend"
    components = panel["components"]
    assert len(components) == 2
    blend_c0 = blend["ranking"]["panel_scoring"]["components"][0]
    assert {
        k: components[0][k]
        for k in ("artifact_path", "expected_content_sha256",
                  "expected_config_fingerprint")
    } == {
        k: blend_c0[k]
        for k in ("artifact_path", "expected_content_sha256",
                  "expected_config_fingerprint")
    }
    c1 = components[1]
    assert c1["kind"] == "momentum_residual"
    assert c1["artifact_path"] == "artifacts/momentum/momentum_artifact_ledger.jsonl"
    assert c1["expected_config_fingerprint"] == "momentum-v0-fd65161a20b29314"
    assert "expected_content_sha256" not in c1  # pipeline#261 refuses it
    # Single source: the ledger path must equal the prod config's slow
    # momentum shadow leg (the lane this blend leg reuses).
    mom_leg = next(
        m
        for m in prod["ranking"]["panel_scoring"]["shadow_models"]
        if m["name"] == "momentum_residual_v0_shadow"
    )
    assert c1["artifact_path"] == mom_leg["artifact_path"]

    # 2-6. identical delta set to the clf blend, then full equality after
    # normalizing the SAME declared deltas — the two blend profiles must be
    # the same lane construction, differing only in component 1.
    assert panel["global_calibration"]["enabled"] is False
    assert panel["conviction_gate"]["enabled"] is False
    assert mom["ranking"]["kelly_sizing"]["enabled"] is False
    assert mom["rotation"]["joint_actions"]["qp_mu_contract"] == "strict"
    assert mom["ranking"]["alpha_to_mu"]["enabled"] is True
    assert "shadow_models" not in panel
    assert "shadow_experiment" not in panel
    assert mom["wash_sale_min_material_npv"] == 1.00
    assert panel["buy_floor"] is None
    assert mom["model_sell"]["panel_veto"]["enabled"] is False
    assert mom["rotation"]["panel_buy_floor"] is None
    assert mom["rotation"]["panel_sell_floor"] is None
    assert mom["rotation"]["panel_buy_rank_floor"] is None
    gate = mom["rotation"]["joint_actions"]["qp_admission_gate"]
    assert gate["min_rank_score"] is None
    assert gate["topup_min_rank_score"] is None
    assert gate["min_expected_return_by_regime"] is None

    # The two blend profiles are byte-equal after stripping provenance and
    # popping ONLY component 1 (the single declared difference).
    blend_norm = _strip_provenance(blend)
    mom_norm = _strip_provenance(mom)
    for cfg in (blend_norm, mom_norm):
        cfg["ranking"]["panel_scoring"]["components"] = (
            cfg["ranking"]["panel_scoring"]["components"][:1]
        )
    assert mom_norm == blend_norm
