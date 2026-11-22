# Active Buildathon Submission — User Confirmation

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
- Competition receipt: **UNKNOWN**
- Official practice score: **PENDING/UNKNOWN**
- Existing best recorded official practice score: **2.92**
- Best score commit: 76dcb1f15e5b4d27db9e2a196deef6916ac54a04
- Selected final entry: keep the 2.92 winner unless a higher official score is verified.

Do not conflate this report commit with the source submitted to the competition.
Never change the historical candidate commit or submit a ledger-only commit.
The other validated but unsubmitted experimental candidate is
beede6315d13da949fcf87943d916797d994d7c8
(recovery-cover combination), and it must not be submitted without checking
current quota and whether a stronger official result is already known.

Next: retrieve the authenticated official score when a supported authorized
route is available or after the user supplies their result; enter exact receipt,
status and score in reports/experiments.json. Respect the November 22 11:00 AM
EST cutoff and the official team submission limit.

## Additional prepared survival experiment (not submitted)

- Branch: experiment/solo-unseen-fire-escape-2026-11-21
- Exact source commit: 6f24f0019b81c559275bbcd405b92f4f60eb0f83
- CI run: https://github.com/mbaglo/MechRoyale-Agent/actions/runs/44977788911
- Validation: **61 regression tests passed**, linux/amd64 Docker build passed,
  official conformance checker **300/300**, zero late or missing replies.
- Official score: **UNKNOWN**; never infer score from conformance.
- Submission: **NOT submitted**. Do not submit before checking the user-confirmed
  mortar candidate's score and quota.
- Hypothesis: when the mech is already idle within a safe zone and is damaged
  by an unseen shooter, a brief collision-checked retreat/side-step from the
  confirmed attack bearing may improve survival. Preserve visible combat,
  supply capture, resource pursuit and urgent zone routes.
- Safety: triggers only on valid directional *damage* events; mere distant
  sounds do not trigger. Fully isolated from the mortar candidate and best entry.

[CHATGPT_ENHANCEMENT_2026-11-21] Source was branched from best 2.92 commit,
not from the already-submitted mortar candidate; no changes to original score
or entry selection were made.
