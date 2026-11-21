"""[CODEX_ENHANCEMENT_2026-11-21] Static geometry and terrain queries."""
import array
import json
import math
import sys
from pathlib import Path


def inside(x, y, ring):
    hit = False
    j = len(ring) - 2
    for i in range(0, len(ring), 2):
        ax, ay, bx, by = ring[i], ring[i+1], ring[j], ring[j+1]
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            hit = not hit
        j = i
    return hit


class World:
    def __init__(self, directory):
        self.prisms = []
        self.cells = {}
        self.terrain = None
        self.heights = None
        self.bounds = None
        path = Path(directory) / 'v2'
        try:
            data = json.loads((path / 'world.json').read_text())
            self.bounds = data['bounds']
            self.terrain = data['terrain']
            self.heights = array.array('h')
            self.heights.frombytes((path / 'terrain.i16').read_bytes())
            if sys.byteorder != 'little':
                self.heights.byteswap()
            if len(self.heights) != self.terrain['nx'] * self.terrain['ny']:
                raise ValueError('terrain size mismatch')
            for p in data['prisms']:
                r = p['ring']
                box = (min(r[::2]), min(r[1::2]), max(r[::2]), max(r[1::2]))
                idx = len(self.prisms)
                self.prisms.append((p, box))
                for ix in range(math.floor(box[0]/32), math.floor(box[2]/32)+1):
                    for iy in range(math.floor(box[1]/32), math.floor(box[3]/32)+1):
                        self.cells.setdefault((ix, iy), []).append(idx)
        except (OSError, ValueError, KeyError) as exc:
            raise RuntimeError(f'cannot load official arena: {exc}') from exc

    def ground(self, x, y):
        t = self.terrain
        fx = min(t['nx']-1.00001, max(0, (x-t['minX'])/t['step']))
        fy = min(t['ny']-1.00001, max(0, (y-t['minY'])/t['step']))
        i, j = int(fx), int(fy)
        u, v = fx-i, fy-j
        k = j*t['nx']+i
        h = self.heights
        return ((h[k]*(1-u)+h[k+1]*u)*(1-v) +
                (h[k+t['nx']]*(1-u)+h[k+t['nx']+1]*u)*v)*t.get('scale', .01)

    def solid(self, x, y, z):
        for idx in self.cells.get((math.floor(x/32), math.floor(y/32)), ()):
            p, b = self.prisms[idx]
            if b[0] <= x <= b[2] and b[1] <= y <= b[3] and p['base'] < z < p['top']:
                if inside(x, y, p['ring']) and not any(inside(x, y, h) for h in p.get('holes', [])):
                    return True
        return False

    def clear(self, a, b):
        # Conservative sampled ray; firing only, never authoritative physics.
        n = max(1, math.ceil(math.dist(a, b)/2))
        for i in range(1, n):
            f = i/n
            x, y, z = (a[k]+(b[k]-a[k])*f for k in range(3))
            if self.solid(x, y, z) or z < self.ground(x, y):
                return False
        return True

    def walkable(self, start, end, stats):
        radius = stats.get('radius', 2.5)
        height = stats.get('height', 9)
        n = max(1, math.ceil(math.dist(start[:2], end[:2])/1.5))
        old = self.ground(*start[:2])
        roof = start[2] > old + stats.get('step_up', 1.2)+1
        for i in range(1, n+1):
            f = i/n
            x, y = (start[k]+(end[k]-start[k])*f for k in range(2))
            b = self.bounds
            if not (b['minX']+radius <= x <= b['maxX']-radius and b['minY']+radius <= y <= b['maxY']-radius):
                return False
            ground = self.ground(x, y)
            if not roof and ground-old > max(stats.get('step_up', 1.2), 1.5*math.tan(math.radians(stats.get('max_slope_deg', 50)))):
                return False
            feet = max(ground, start[2]) if roof else ground
            for dx, dy in ((0,0),(radius,0),(-radius,0),(0,radius),(0,-radius)):
                if any(self.solid(x+dx, y+dy, feet+dz) for dz in (.2, height*.5, height-.1)):
                    return False
            old = ground
        return True
