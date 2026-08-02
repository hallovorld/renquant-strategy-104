# Wash-sale materiality floor: the policy design lands in its owning repo

STATUS: proposal (design-only; zero behavior change — the knob is specified at
default 0.0 and not yet added to any config file).
WHAT: doc/design/2026-08-02-wash-sale-materiality-floor.md — the policy knob
(`risk.wash_sale.materiality_floor_usd`, default 0.0 = today's behavior), the
estimate contract (same lot engine incl. same-event netting; conservative
ceil; unavailable → block stands), the full AC6 governed-override triplet
(reviewed-PR-only identity; $50 design ceiling; per-decision run-bundle stamp
with config fingerprint), and the 4-step rollout order.
WHY/DIR: measured on the live book — the mass block zeroed buys on 3 of 5
sessions protecting ~$15 total (one instance $0.04) while $6,868 sat idle
`[VERIFIED — pipeline#223 / the orch deployment-blockers record]`. The
proposal was ordered re-homed here (policy owner) from orch#607's corrected
record.
EVIDENCE:
  artifact:      doc/design/2026-08-02-wash-sale-materiality-floor.md
  prod or exp:   exp — design doc only; no config file touched in this PR
  existing data: the 3-of-5-sessions / ~$15 / $0.04 / $6,868 measurements are
                 pipeline#223's and the deployment-blockers record's, cited
                 not re-measured `[早前实测]`
  best-known?:   yes — first materiality proposal in the policy repo; the only
                 prior knob is wash_sale_days=30
  scope:         docs-only here; enforcement + invariance proof are
                 pipeline#223's PR; nothing changes until pins + an explicit
                 non-zero floor config PR
NEXT: review here → pipeline#223 implementation (floor=0 A/B invariance +
estimator tests) → operator pin batch → operator floor-setting config PR
(proposed start $5).
