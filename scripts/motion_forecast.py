"""[ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
Local experiment only. The selected agent does not use this forecast.
Estimate how much of an opponent's reported horizontal velocity persists over a gun flight.
"""
from collections import deque
import math


class MotionHistory:
    def __init__(self, mech):
        self.tracks = {}
        self.prior = mech['walk_speed']**2
        self.max_correction = mech['walk_speed']

    def observe(self, now, enemies):
        for enemy in enemies:
            history = self.tracks.setdefault(enemy['id'],deque(maxlen=32))
            if history and now == history[-1][0]:
                continue
            if history and not 0 < now-history[-1][0] < .25:
                history.clear()
            history.append((now,enemy['pos'][:2],enemy['vel'][:2]))

    def velocity(self, enemy, flight):
        raw = enemy['vel']
        history = self.tracks.get(enemy['id'])
        if flight < .18 or not history or len(history)<8:
            return raw
        rows = list(history)
        samples = []
        end = 1
        for stamp,pos,vel in rows:
            due = stamp+flight
            while end<len(rows) and rows[end][0]<due:
                end += 1
            if end == len(rows):
                break
            t0,p0,_ = rows[end-1]
            t1,p1,_ = rows[end]
            weight = (due-t0)/(t1-t0)
            actual = [(p0[k]+weight*(p1[k]-p0[k])-pos[k])/flight for k in (0,1)]
            samples.append((vel,actual))
        if len(samples)<6:
            return raw
        vbar = [sum(v[k] for v,_ in samples)/len(samples) for k in (0,1)]
        ubar = [sum(u[k] for _,u in samples)/len(samples) for k in (0,1)]
        var = sum((v[k]-vbar[k])**2 for v,_ in samples for k in (0,1))
        cov = sum((v[k]-vbar[k])*(u[k]-ubar[k]) for v,u in samples for k in (0,1))
        persistence = max(0,min(1,(cov+self.prior)/(var+self.prior)))
        correction = [ubar[k]+persistence*(raw[k]-vbar[k])-raw[k] for k in (0,1)]
        scale = min(1.,self.max_correction/max(1e-8,math.hypot(*correction)))
        return [raw[0]+scale*correction[0],raw[1]+scale*correction[1],raw[2]]
