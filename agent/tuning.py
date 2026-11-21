"""[CODEX_ENHANCEMENT_2026-11-21] Interpretable policy weights, not fitted scores."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Tuning:
    threat_distance: float = 180.0
    approach_weight: float = .7
    facing_weight: float = .5
    damage_window: float = 2.0
    damage_weight: float = 5.0  # fraction of maximum HP lost in the window
    crossfire_weight: float = 1.2
    trapped_weight: float = 1.0
    low_energy_weight: float = .6
    conservative_pressure: float = 2.5
    emergency_pressure: float = 4.0
    escape_probe: float = 6.0
    route_step: float = 10.0
    route_expansions_per_tick: int = 4
    route_max_nodes: int = 1200
    route_radius: float = 240.0
    reserve_seconds: float = 1.8
    reserve_pressure_seconds: float = .35


DEFAULT = Tuning()
