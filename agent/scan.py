"""[ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
Track which bearings the mech's actual field of view recently covered.
"""
import math


class QuietScan:
    sectors = tuple(2*math.pi*i/12 for i in range(12))

    def __init__(self, vision):
        self.seen = [-math.inf]*len(self.sectors)
        self.half_view = max(0.,math.radians(vision['fov_deg'])/2 - math.pi/12)
        self.hold_time = vision['memory_s']/2
        self.last_contact = -math.inf

    def observe(self, now, facing, enemies):
        if enemies:
            self.last_contact = now
        for i,yaw in enumerate(self.sectors):
            offset = (yaw-facing+math.pi)%(2*math.pi)-math.pi
            if abs(offset) <= self.half_view:
                self.seen[i] = now

    def heading(self, now, facing):
        oldest = min(self.seen)
        if now-oldest < self.hold_time:
            return facing
        options = [((yaw-facing+math.pi)%(2*math.pi)-math.pi,i) for i,yaw in enumerate(self.sectors)
                   if self.seen[i] == oldest]
        # Use the nearest stale sector and break symmetric ties clockwise.
        offset,_ = min(options,key=lambda pair:(round(abs(pair[0]),6),pair[0]))
        return (facing+offset+math.pi)%(2*math.pi)-math.pi
