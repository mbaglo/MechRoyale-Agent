"""[CHATGPT_ENHANCEMENT_2026-11-21] Opportunistic, guarded power-cube farming.

NPC drones drop two cubes each. The prior policy never considered an NPC
a gun target, despite the protocol explicitly granting cubes on drone death.
This module ONLY selects observed drones while no opponent is tracked and
the mech is healthy, in-zone, with a usable gun and no recent threat.
It never guesses unseen NPC locations or approaches them at any cost.
"""
import math


class NeutralFarm:
    """[CHATGPT_ENHANCEMENT_2026-11-21] Conservative drone resource targeting."""

    def __init__(self, world):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Keep the official map and threat history."""
        self.world = world
        self.last_threat = -1e9

    def targets(self, situation):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Return safe observed drone shot options.

        Do not shoot when another mech is visible/tracked, the zone requires
        movement, the health reserve is small, or recent gun/laser/lightning/
        mortar sounds, incoming bullets or actual damage indicate danger.
        A ray test protects the gun from firing into opaque map geometry.
        """
        s = situation
        obs, me = s.obs, s.me
        time = obs['t']
        hostile_sounds = ('gun', 'mortar', 'laser', 'laser_charge',
                          'lightning', 'explosion')
        if (s.damage or any(e.get('type') == 'damaged' for e in obs.get('events', [])) or
                any(x.get('kind') in hostile_sounds and
                    x.get('dist') in ('near','mid') for x in obs.get('sounds', []))):
            self.last_threat = time

        if (s.enemies or s.urgent or s.health < .85 or not me['in_zone'] or
                time-self.last_threat < 4.):
            return []

        position = me['pos']
        if any(math.dist(p['pos'],position) < 65 for p in obs.get('projectiles', [])):
            self.last_threat = time
            return []

        gun = next((w for w in me['weapons'] if w and w['kind'] == 'gun'), None)
        if not gun or gun.get('reload',0) > .05 or gun.get('ammo',0) < 2:
            return []
        maximum = min(170., gun['stats']['range'] - 12.)
        if maximum <= 0:
            return []

        center, radius = obs['zone']['next_center'],obs['zone']['next_radius']
        muzzle = [position[0],position[1],
                  position[2] + me['stats']['muzzle_height']]
        opportunities = []
        for npc in obs.get('mechs',[]):
            if npc.get('kind') != 'npc' or npc.get('hp',0) <= 0:
                continue
            target = npc['pos']
            distance = math.dist(position[:2],target[:2])
            if not 18. < distance < maximum:
                continue
            # Don't create new exposure by engaging outside the next circle.
            if math.dist(target[:2],center) > radius-15.:
                continue
            head_center = [target[0],target[1],target[2]+1.75]
            if self.world.clear(muzzle,head_center):
                opportunities.append(npc)

        return opportunities
