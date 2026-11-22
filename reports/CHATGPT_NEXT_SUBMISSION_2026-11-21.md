# Mech Royale — Next Official Evaluation Decision

[CHATGPT_ENHANCEMENT_2026-11-21]

Reviewed competition/evaluations reports/SCOREBOARD.md, reports/experiments.json,
the selected source at EXP-031, experimental source and GitHub Actions results
at 23:30 America/New_York, November 21, 2026.

## Verified state

- Best official score: **2.92**, EXP-031, commit
  `76dcb1f15e5b4d27db9e2a196deef6916ac54a04`,
  official receipt `BB-33F280F9`.
- The previously user-submitted mortar arc candidate `BB-46438060`
  scored **2.90**, not a new best.
- Recovery combination `BB-CCC1C2D4`: **2.83**.
- Unseen-fire escape `BB-79FE36C6`: **2.90**.
- Covered reload `BB-98EBDC6C`: **2.88**.
- Laser release `BB-C4DF100C`: **2.92** (tie).
- No submitted candidate in this log beats EXP-031.
- Never re-submit these evaluated commits or overwrite the selected entry.

## Priority next candidate for one official practice score

**EXP-041 — pincer-clearance escape, full exact source commit:**

`a0c1204b656e07aaa09eb6d641e412aafc46fad8`

- Branch: `experiment/astra-pincer-clearance-041`
- CI: https://github.com/mbaglo/MechRoyale-Agent/actions/runs/44982586788
  **success** (unit tests, Linux AMD64 Docker, official protocol check).
- Engineering hypothesis: when already at a fixed inner-zone goal and
  two opponents flank the mech, consider collision-checked lateral escapes
  rather than holding stationary. When no projectile needs dodging, reject
  escape steps reducing clearance to the nearest observed flank.
- Evidence: on 18 feasible synthetic paired-closing layouts, with a
  ground-acceleration approximation, mean nearest-enemy clearance change
  was -9.986 m for EXP-031 vs -3.184 m for EXP-041 after two seconds;
  worst -10.0 m vs -9.743 m. This is a navigation geometry probe, **not**
  an official match, HP simulation, or score prediction.
- This is a distinct survival improvement and has stronger cross-map
  evidence than the sibling EXP-040, which regressed in its worst case.
- Submission: **NOT submitted** as of this log; official score unknown.

## Other worthwhile unscored candidates

- EXP-039 `822ac93441bc3cad45b03803362062961ccbb33c`:
  guarded gun-only NPC farming to collect two-cube drops, CI success;
  official score unknown. Unlike EXP-041, unchanged actions on the only
  available 300-observation replay. Keep separately validated; do not
  combine unscored strategies.
- EXP-038 `8e2da949c413cf109f34d8cb8f339c87fec77dbd`:
  suppress unnecessary urgent zone retreat if safely inside the next
  circle; CI success, no recorded action changes; score unknown.
- EXP-040 `3dfbe14dcceaf5c1cbf91b9d51b9809b71e3a846`:
  earlier pincer escape; CI success but worse downside than EXP-041 in
  the documented synthetic ground-acceleration probe. Hold pending 041.

## Submission guardrails

1. Obtain *current* competition quota and active/pending submissions from
   the **authenticated official** Buildathon interface; repository history
   alone does not prove quota is available.
2. Submit at most **one** validated exact hash to evaluate this idea.
3. Do not claim an official score until the page explicitly says Scored.
4. Only replace EXP-031's final selection if the new **official score
   exceeds 2.92**.
5. If a competition browser isn't actually available and authenticated,
   keep the exact hash ready for manual submission and continue other
   repository work. Do not fake a submission, pending receipt or score.
6. End submissions before Sunday November 22, 2026 11:00 AM EST.

[CHATGPT_ENHANCEMENT_2026-11-21] This report is informational metadata,
not the competition source commit and not a submission.
