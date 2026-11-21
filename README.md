# MechRoyale-Agent
Autonomous AI combat agent for Builders Buildathon 2026. Features adaptive combat strategies, intelligent navigation, opponent tracking, survival optimization, and simulation-driven decision-making.

[CODEX_ENHANCEMENT_2026-11-21]

**EXP-011 magazine-priority candidate:** `experiment/best-magazine-priority-2026-11-21`,
based on selected official **2.25** source `2f30e3d217461379eedebeea49751b6209397c79`.
Only the `gun_mag` upgrade preference changes (62 to 115). The official score is
unknown. Goal remains official **10.00+**; see `reports/EXP-011.md` and the ledger.

**EXP-004:** branch `experiment/v1-weapon-reach-2026-11-21`, based directly on
V1 `8a87e8a467dde525d25fcf9cb5181087c6e55fd7`. Its only tactical change is
weapon-search radius: 65 to 130 meters. Existing safety filters are preserved.
The official 300-observation replay produced no changed actions; synthetic tests
cover the additional safe pickup opportunities. Official performance is unknown.
Keep the verified 2.10 V1 entry selected. See `reports/experiments.json` for results.

Working deterministic Python agent for `mechfight/1`, using only the standard
library and official starter kit. **Gameplay strength is unmeasured:** the kit
has no simulator. The original project description above describes the intended
system; simulation-driven optimization requires official match results.

## Run and test

Python 3.11+ locally; the Docker image uses Python 3.13.9.

```sh
python -m unittest discover -s tests -v
python official/mechfight-kit/check/check.py -- python -u bot.py
python scripts/benchmark.py
docker build --platform linux/amd64 -t mechroyale-agent .
python official/mechfight-kit/check/check.py --map-dir /arena -- docker run --rm -i --network none --cpus 1 --memory 512m --memory-swap 512m --pids-limit 128 --cap-drop ALL --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "$PWD/official/mechfight-kit/arena:/arena:ro" mechroyale-agent
```

The final command is POSIX shell syntax. In PowerShell replace the volume argument
with `"${PWD}/official/mechfight-kit/arena:/arena:ro"`.
The arena is mounted externally in matches; the image deliberately excludes the kit.
Running `python bot.py` alone waits for server JSON lines on stdin.

## Design

- `agent/observation.py`: health, threats, damage events, bounded opponent tracking,
  and advance warning of zone travel requirements.
- `agent/strategy.py`: aggressive for isolated vulnerable opponents; balanced
  when healthy; conservative when hurt, outnumbered or under zone pressure.
  Health hysteresis prevents repeated mode switching.
- `agent/navigation.py`: 16 movement directions plus stationary candidate,
  terrain/prism collision checks, zone penalties, cover preference, projectile
  avoidance and stuck escape behavior. Saves energy for retreat and zone travel.
- `agent/combat.py`: target persistence, line-of-fire checks, projectile intercepts,
  low-arc mortar aiming, laser charge/release, lightning range/energy checks,
  reload management and actual torso alignment. Retreat suppresses distant fire
  to permit regeneration. Aim also controls vision and front armor.
- `agent/world.py`: bilinear terrain sampling and spatially indexed building,
  bridge and polygon-hole queries. Trees affect sight but do not stop shots.
- `agent/policy.py`: the single authoritative `Bot.act` action selector,
  upgrades and reachable weapon pickup handling.
- `mechfight.py`: official typed transport wrapper, queued-observation handling,
  flushed JSON output, clean end and stderr exception diagnostics.

Live weapon and mech numbers come from observations/config. No match-time network,
dependencies, subprocesses or disk writes. State resets per match. All match
decisions are deterministic; no private match seeds are inferred.

Navigation and shot collision tests are sampled approximations, not a reproduction
of authoritative physics. Navigation is local and can struggle around complex
concave buildings. Mortar aiming uses an approximate lead and does not simulate
the entire ballistic path. These are known limitations requiring match evidence.

## Actual validation and remaining blockers

November 21, 2026, Windows development host:

- Ten automated tests passed, including all 300 recorded observations with schema,
  tick, finite-number, movement and runtime checks.
- Official checker passed: 300/300 in time, zero late/missing/invalid actions,
  zero stale replies; p50 3.5 ms, p90 7.3 ms, p99 9.1 ms, maximum 9.4 ms.
- These are replay-input tests, **not simulations**. Placement, survival duration,
  win rate, damage and official score remain unavailable. See `reports/benchmark.json`.
- Docker is not installed on the development host. GitHub Actions successfully
  built linux/amd64 and passed all ten tests and the official checker under the
  competition sandbox for source commit `85de6f8`:
  https://github.com/mbaglo/MechRoyale-Agent/actions/runs/44910472403

The repeat local checker after the initialization fix also passed 300/300, with
p50 3.5 ms, p99 9.1 ms and maximum 10.1 ms. Container check success is verified
from the completed CI job; local timings above are not container timings.

No gameplay improvement is claimed. Test scenarios check intended behavior;
they do not establish competitive strength. Use the official 48-match practice
evaluation before changing policy weights, and preserve each evaluated commit.

## Submit

Public repository: https://github.com/mbaglo/MechRoyale-Agent

1. Confirm the validation workflow succeeds for the exact submitted commit.
2. Sign in at https://www.joinbuilders.org/buildathon/tracks/builders and submit
   the repository URL using its submission form. The user must complete account
   registration/team eligibility and any authenticated submission steps.
3. Record the commit, scorer version, official mean `16 - place`, and available
   feedback. Practice allows four submissions/hour and 48 matches per submission
   against 15 cooperating house bots. Do not treat replay tests as a practice score.
4. Select the final entry before **November 22, 2026, 11:00 AM Eastern (EST)**.

Scorer `builders-3`: first eliminated scores 0, winner scores 15, simultaneous
deaths share placement, timeout survivors rank by HP. Final qualifying and finals
use free-for-all matches against entrants, unlike the practice house squad.
Track rules require the repository and submitted commits remain public until
results are published, a root Dockerfile, at most 20 MB at the submitted commit,
and a build within ten minutes. See the preserved `official/protocol.md` for the
complete protocol and `official/SOURCES.md` for provenance.

New competition code is MIT licensed; existing LICENSE attribution is preserved.
The only pre-existing code used is the organizer-provided wrapper and kit,
preserved and attributed in `official/`. No paid infrastructure is required.
