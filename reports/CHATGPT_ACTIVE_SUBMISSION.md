# Active Buildathon Submission — User Confirmation

## Current competition status (November 22)

- **Selected best:** EXP-044, **3.06**, exact source commit `b0d240270a180f2f5a5b4a238e7a9faf1afa58e6`, receipt `BB-2F33846B`. Verified in the authenticated competition-result ledger.
- Mortar `BB-46438060`: **2.90**. Recovery combination `BB-CCC1C2D4`: **2.83**. Unseen-fire escape `BB-79FE36C6`: **2.90**. All have been scored; do not resubmit.
- **Most recently validated unsubmitted candidate:** guarded charging-laser lane escape, exact source `2765aa19ecec0bb3d51a19424af2650badbe2b2e`, GitHub Actions [45023768984](https://github.com/mbaglo/MechRoyale-Agent/actions/runs/45023768984): 71 unit tests, Linux AMD64 Docker, official checker 300/300. Competitive score **unknown**. Earlier safe-supply staging `3544e1a28f4f7aa43ee125f08ac1af98f366201a` and other unsubmitted candidates remain separate in `reports/experiments.json`.
- The bot is **not** authorized for an authenticated competition-browser submission through available connected tools in this session. No new submission was made. Reconcile live quota and any external submissions before submitting manually.
- Deadline: November 22, 2026, **11:00 AM America/New_York**. This status supersedes historical point-in-time instructions below.


[CHATGPT_ENHANCEMENT_2026-11-21]

The user confirmed that the **mortar covered-target candidate was submitted** to
the Buildathon on November 21, 2026. Codex was already stopped before ChatGPT
resumed engineering. Do not restart Codex or submit the same candidate again.

- Repository: mbaglo/MechRoyale-Agent
- Candidate branch: experiment/solo-mortar-covered-target-2026-11-21
- Exact source commit: 65feeefda930083bb4701a148afbfc40f92c6008
- Source CI: https://github.com/mbaglo/MechRoyale-Agent/actions/runs/44974851691
- CI: **SUCCESS**
- Competition submission: **USER CONFIRMED**, not independently seen in competition UI
- Competition receipt: **BB-46438060** (user reported)
- Official practice score: **2.90** (Scored, user reported)
- Best recorded official practice score **at this historical point**: **2.92** (later surpassed by 3.06)
- Best score commit: 76dcb1f15e5b4d27db9e2a196deef6916ac54a04
- Selected final entry **now**: EXP-044 at **3.06**, not this mortar submission.

Do not conflate this report commit with the source submitted to the competition.
Never change the historical candidate commit or submit a ledger-only commit.
The recovery-cover combination `beede6315d13da949fcf87943d916797d994d7c8`
was subsequently submitted (`BB-CCC1C2D4`) and scored **2.83**. Do not resubmit.

Score and receipt have now been supplied by the user and recorded in
reports/experiments.json and reports/SCOREBOARD.md. This experiment is below
2.92; do not promote it. Respect the November 22 11:00 AM
EST cutoff and the official team submission limit.

## Additional prepared survival experiment (not submitted)

- Branch: experiment/solo-unseen-fire-escape-2026-11-21
- Exact source commit: 6f24f0019b81c559275bbcd405b92f4f60eb0f83
- CI run: https://github.com/mbaglo/MechRoyale-Agent/actions/runs/44977788911
- Validation: **61 regression tests passed**, linux/amd64 Docker build passed,
  official conformance checker **300/300**, zero late or missing replies.
- Official score: **2.90** (later authenticated result; not inferred from conformance).
- Submission: **Scored** (later receipt `BB-79FE36C6`); do not resubmit.
  Check the current quota and pending entries before any new submission.
- Hypothesis: when the mech is already idle within a safe zone and is damaged
  by an unseen shooter, a brief collision-checked retreat/side-step from the
  confirmed attack bearing may improve survival. Preserve visible combat,
  supply capture, resource pursuit and urgent zone routes.
- Safety: triggers only on valid directional *damage* events; mere distant
  sounds do not trigger. Fully isolated from the mortar candidate and best entry.

[CHATGPT_ENHANCEMENT_2026-11-21] Source was branched from best 2.92 commit,
not from the already-submitted mortar candidate; no changes to original score
or entry selection were made.
