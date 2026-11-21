# EXP-NPC01: safe power-cube acquisition from ranged NPC drones

[CHATGPT_ENHANCEMENT_2026-11-21]

Base: official-best commit `4ba12f9cf9da12dbdcbe35dc104a352879347414`, score **2.46**.
Branch: `experiment/best246-npc-cube-opportunity-2026-11-21`.
This experiment has **not** been officially scored. Do not replace the selected entry based on protocol validation.

## Verified omission in the baseline source

- `Observer.parse()` includes only `kind == "mech"` in `s.enemies`.
- `Combat.act()` only targets `s.enemies` or crates; it never targets NPC drones.
- `official/protocol.md` specifies each NPC drone is 350 HP and drops **two power cubes** on death; power cubes increase health/damage, and trigger upgrade choices.
- `Strategy.goal()` on the selected baseline pursues safe visible cubes within 130 m, but not beyond. The experiment's drone engagement window is **95–125 m** so a kill's cubes can be pursued without changing this original search radius.

## One isolated tactical hypothesis

When **no player mechs are visible**, our mech is at least **85% HP**, inside the zone, not under attack, in non-Conservative mode, and has at least **8 loaded gun rounds**, opportunistically aim at an observed drone 95–125 m away. Use the starting gun, never charge/spend secondary weapons on it.

The baseline wrongly uses the height of a mech (4.5 m) for a selected non-crate target. This experiment explicitly uses the NPC's center at **1.75 m** above its feet (protocol NPC height 3.5 m). The first target-screening ray already used 1.75 m but shot aiming used 4.5 m.

The baseline movement, enemy targeting, fallback scanning, mode selection, gun cooldown/ammo checks, upgrade policy, and cube-goal logic are otherwise preserved. There is no NPC pursuit or hard-coded match seed.

## Validation and submission discipline

- Run the 6 new tactical regression tests, existing suite and official 300-observation checker.
- Require green exact-source Linux AMD64 Docker sandbox CI under the 50 ms decision limit.
- These are **not** interactive battle results. The current leaderboard score remains **2.46** until official scoring proves otherwise.
- Do not submit if an existing authorized Codex session is scoring another candidate or if quota is tight. At most one submission per exact hash. The competition site may accept the public repo URL plus full candidate commit.
- Compare only the official mean `16 - place` from 48 practice matches.
- Protect all existing branches and original trading projects; do not merge into `main` or replace the 2.46 final entry without a better result.

## Potential failure modes

- Farming may interrupt regeneration or attract mechs through gunshots.
- Even 95–125 m kills still require traveling to collect cubes and avoiding newly arrived enemies.
- Target health, weapon lethality and enemy positions change throughout matches.
- Two cube drops are an opportunity, not proof of improved practice placement.

The target remains >=6.0 then >=10.0, but an unscored candidate is not an improvement.
