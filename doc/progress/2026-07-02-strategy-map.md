# Strategy map pointer doc — docs PR

STATUS:   docs only.
WHAT:     `doc/strategy-map.md` — the strategy-facing map (objective equation + where the
          measured state lives + signal roster present/planned/closed + the policy knobs
          this repo owns + the change protocol). POINTER format by design: canonical
          numbers/specs live in orchestrator and are linked, never hand-copied — the
          umbrella strategy-104.md hand-snapshot rot is the counterexample this avoids.
WHY:      operator (2026-07-02): the strategy repo should carry its own map. Per the #210
          ownership split it should — policy is this repo's; the map states what applies
          here and where the living truth is.
NEXT:     review; the M9 generated-snapshot work (orchestrator A6 follow-up) will link back
          to this map.
