# Wash-sale materiality floor: the policy design lands in its owning repo

STATUS: proposal (design-only; zero behavior change — the knob is specified at
default 0.0 and not yet added to any config file).
WHAT: doc/design/2026-08-02-wash-sale-materiality-floor.md — the policy knob
(`risk.wash_sale.materiality_floor_usd`, default 0.0 = today's behavior), the
estimate contract (same lot engine incl. same-event netting; conservative
ceil; unavailable → block stands; the zero-floor short-circuit is now a
NORMATIVE rule — `estimate <= floor` is evaluated only when `floor > 0`, not
merely documented in the JSON `_note`), the full AC6 governed-override
triplet (reviewed-PR-only identity; $50 design ceiling
`[ASSUMED — design ceiling proposal]`; per-decision run-bundle stamp
with config fingerprint), and the 4-step rollout order — pipeline#223's
floor=0 invariance proof must now include both a captured-session A/B AND a
constructed `estimate == $0.00` unit test, since a captured session can pass
without ever exercising that boundary.
WHY/DIR: the design stands on a code-surface mechanism gap (a hard buy gate
with no materiality notion, no proportionality, no governed override), NOT on
any particular week's dollar figures; in-session confirmation that the gate
fires as a structural block: the 2026-07-29 FunnelIntegrityAlert names
wash_sale_mass_block among fired conditions `[VERIFIED —
logs/daily_104/2026-07-29.log, read 2026-08-02]`. Magnitude figures are cited
from pipeline#223 as context only and are explicitly NOT this design's
decision basis (design §1). Re-homed here per orch#607's corrected record.
EVIDENCE:
  artifact:      doc/design/2026-08-02-wash-sale-materiality-floor.md
  prod or exp:   exp — design doc only; no config file touched in this PR
  existing data: in-session — the 2026-07-29 STRUCTURAL_BLOCK alert naming
                 wash_sale_mass_block `[VERIFIED —
                 logs/daily_104/2026-07-29.log, read 2026-08-02]`; magnitude
                 figures cited from pipeline#223 as context only, explicitly
                 not this design's decision basis (design §1)
  best-known?:   yes — first materiality proposal in the policy repo; the only
                 prior knob is wash_sale_days=30
  scope:         docs-only here; enforcement + invariance proof are
                 pipeline#223's PR; nothing changes until pins + an explicit
                 non-zero floor config PR
NEXT: review here → pipeline#223 implementation (floor=0 A/B invariance,
captured-session AND constructed `estimate == $0.00` case, + estimator
tests) → operator pin batch → operator floor-setting config PR
(proposed start $5 `[ASSUMED — proposed initial operator floor]`).
