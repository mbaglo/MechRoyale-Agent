"""[CHATGPT_ENHANCEMENT_2026-11-21] Short-lived last-seen resource navigation.

The official protocol reveals cubes and weapon pickups only while in view.
A tracked resource can leave the 120-degree vision wedge solely because the
mech turns to scan or face a threat. Remembering its *observed* position
briefly avoids aborting a safe approach on one missing observation.

Never invent an item location, pursue unseen supplies indefinitely, or
override the original zone, health, opponent, terrain and inventory filters.
"""
import math


class ResourceMemory:
    """[CHATGPT_ENHANCEMENT_2026-11-21] Bounded, observed loot intent memory."""

    def __init__(self):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Store only reported cube/weapon locations."""
        self.items = {}

    def candidates(self, situation):
        """[CHATGPT_FIX_2026-11-21] Offer safe short-lived last-seen loot.

        Actual visible objects are always handled by Strategy.goal first.
        A last-seen object is dropped after 2.5 s, and immediately when the
        mech is near its old position but cannot see it (likely collected).
        A large health reserve and absence of threats are required.
        """
        s = situation
        o, me = s.obs, s.me
        now = o['t']
        pos = me['pos']
        visible = set()
        for kind, field in (('cube', 'cubes'), ('weapon', 'pickups')):
            for item in o.get(field, []):
                key = kind, item['id']
                visible.add(key)
                # Copy only the fields needed for a later recheck. No guesses.
                self.items[key] = (now, dict(id=item['id'],
                                            kind=item.get('kind'),
                                            pos=list(item['pos'])))
        # A bounded cache is important with 36 crates and 40 floor pickups.
        for key, (seen_at, item) in list(self.items.items()):
            separation = math.dist(pos[:2], item['pos'][:2])
            nearby_but_absent = (key not in visible and separation < 8. and
                                 abs(pos[2]-item['pos'][2]) < 4.)
            if now - seen_at > 2.5 or nearby_but_absent:
                del self.items[key]
        if len(self.items) > 100:
            for key, _ in sorted(self.items.items(),
                                 key=lambda pair: pair[1][0])[:-100]:
                del self.items[key]

        # This memory is optional: never tempt the agent away from an enemy,
        # a threatened position, or a required zone retreat.
        if (s.urgent or s.enemies or s.damage or s.health < .70 or
                not me['in_zone']):
            return []
        if any(math.dist(p['pos'],pos) < 65
               for p in o.get('projectiles', [])):
            return []
        if any(x.get('kind') in ('gun','mortar','laser','laser_charge',
                                 'lightning','explosion') and
               x.get('dist') in ('near','mid')
               for x in o.get('sounds', [])):
            return []

        free_slot = any(w is None for w in me['weapons'])
        held = {w['kind'] for w in me['weapons'] if w}
        results = []
        for (kind, key_id), (seen_at, item) in self.items.items():
            if (kind, key_id) in visible:
                continue  # The original visible-resource selection owns it.
            if kind == 'cube':
                results.append((item, 1.25, 130.))
            elif kind == 'weapon' and free_slot and item['kind'] not in held:
                results.append((item, 1.06, 130.))
        return results
