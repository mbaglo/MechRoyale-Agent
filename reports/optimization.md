# Squad-survival optimization

[CODEX_ENHANCEMENT_2026-11-21]

Branch: `optimization/squad-survival-2026-11-21`.
Baseline: `8a87e8a467dde525d25fcf9cb5181087c6e55fd7`, kept on `main`.
Official baseline: **2.10**, submission `BB-6CB32C3E`, supplied by the user.
Candidate official score: **not evaluated**. Target: above 3.0.

## Corrections and additions

- Observation pressure weights distance, approach speed, facing, weapon loadout,
  charging, observed attackers, two-second damage history, directional spread,
  walkable escape sectors and low energy. A visible bystander receives a lower
  weight than a pursuer. Enemy coordination is inferred only from observations;
  the same policy can operate in free-for-all finals.
- Aggression now requires an isolated vulnerable opponent, usable weapon range,
  health, energy, escape availability and zone safety. Emergency is an additional
  behavior flag inside conservative mode, preserving the original three modes.
- Retreat goals favor the less pressured side of the next circle. Travel includes
  a detour allowance and starts earlier. Late phases shorten resource detours;
  pressure suppresses contested supply-drop/loot excursions.
- Incremental ground A* expands at most four nodes per decision, with a 1,200-node
  cap and 240 m search radius. It checks terrain, full body clearance and the final
  goal link. Cached routes/edges invalidate on goal movement, mech size changes,
  age or disconnection. Unfinished, failed, rooftop and airborne searches fall
  back to the preserved 16-direction planner. Fixed work limits keep decisions
  deterministic without a hardware-dependent timeout in the policy.
- The local planner retains projectile avoidance and stuck recovery, adds a
  second clearance step against dead ends, weights separation by threat intent,
  and bounds cover rays to the closest three enemies. All six closest enemies
  still affect separation; all visible enemies affect pressure.
- Cylinder footprint/polygon-edge clearance replaces repeated body probes and
  catches thin slabs, corners and hole boundaries. The old sampled-body method
  remains available. Terrain slope uses actual segment length.
- Boosting requires a reason and preserves a pressure/health-dependent reserve.
  Recovery hysteresis prevents rapid spending/recovery oscillation. Emergencies,
  collision-course projectiles and being outside the zone may spend the reserve.
  Routine retreat never commands an airborne jet simply because enemies exist.
- Combat retains gun, mortar, laser and lightning logic. Target ranking includes
  observed threat and persistence. Selection rejects unavailable weapons and
  avoids starting a movement-slowing laser charge in emergencies. Gun shots check
  their own intercept when sharing aim with a secondary. Mortar uses tube height,
  pitch feasibility and a sampled arc. Lightning preserves escape energy, and
  reload can start at distance during retreat. Close defensive fire remains enabled.

Weights and limits are defined in `agent/tuning.py`. They are interpretable
engineering choices, not parameters fitted to official seeds or match outcomes.

## Validation

Run:

```sh
python -m unittest discover -s tests -v
python official/mechfight-kit/check/check.py -- python -u bot.py
python scripts/compare_policy.py
```

The comparison script loads the exact baseline source from Git objects without
changing any checkout. It runs three passes over 300 official recorded inputs and
three passes over 60 crowded synthetic inputs with 15 approaching opponents and
16 projectiles. It records decision cost, mode/boost/fire choices and route use.
The inputs do not react to actions: these are **not matches or survival estimates**.
`reports/optimization-comparison.json` contains measured results. The historical
`reports/benchmark.json` remains attached to baseline source validation.

Final local validation on November 21, 2026:

- 28 tests passed, including the 12 preserved/extended agent tests and 16 tactical
  tests for pursuit, crossfire, escape, zone travel, blocked routing, projectile
  avoidance, energy recovery, weapon handling and stuck/size-change recovery.
- Official checker: 300/300 in time, zero late/missing/stale/invalid responses;
  p50 3.5 ms, p90 7.2 ms, p99 10.5 ms, maximum 11.6 ms.
- Three-pass input comparison: candidate recorded-input p99 9.50 ms and crowded
  p99 11.85 ms, maxima 12.28 ms and 11.86 ms. Baseline p99 was 8.08 ms and
  18.86 ms respectively on this host. This is one machine's timing evidence.
- Recorded-input boost fraction was 23.0% versus baseline 23.67%; firing fraction
  remained 7.33%. In the synthetic emergency fixture both versions boosted on
  every frame because inputs keep supplying energy and pressure. These numbers
  do not measure energy consumed or damage dealt in a live match.

Docker and a Linux WSL distribution are absent locally. Local tests and official
checker run before the candidate commit. Building and checking the new image
requires the branch's GitHub Actions workflow after pushing the commit. The
workflow verifies linux/amd64, one CPU, 512 MB/no swap, no network, uid 65534,
read-only root, a 64 MB `/tmp`, 128 process limit and dropped capabilities. CI
also exports its input benchmark as an artifact. A candidate is ready for official
practice only once that exact commit's workflow succeeds.

## Limitations and next evaluation

No new official matches have been run. Do not infer a score increase from input
tests, a smaller processing cost, routing success or less firing/boosting. The kit
does not contain a simulator or the cooperating house-bot implementations.

Pressure uses facing/velocity as intent proxies; remembered enemies can remain
threats behind cover. Ground routing does not plan roof climbs, cannot explore
beyond its search bounds, and can reject narrow but navigable corridors. Moving
opponents are handled by the local planner, not a dynamic global graph. Collision
rays/ballistic arcs remain sampled; no exact physics equivalence is claimed.
Synthetic stress covers a crowded case, not every possible observation size.

Submit the candidate separately through the signed-in Mech Royale track page;
use the optimization branch and exact full commit if the form allows selecting
them. If the form requires a GitHub URL, use the branch URL:
`https://github.com/mbaglo/MechRoyale-Agent/tree/optimization/squad-survival-2026-11-21`
and verify the resulting submission resolves the intended commit. Do not move
`main` just to submit. Preserve the 2.10 submission and leave final-entry selection
unchanged until the candidate's 48-match result is available. Record its submission
ID, full commit, score and available feedback for the next iteration.
