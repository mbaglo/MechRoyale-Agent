"""[ASTRA_ENHANCEMENT_2026-11-21] Ground-travel comparison on the official static arena.

These deterministic obstacle crossings measure navigation only. They do not simulate matches.
"""
import gzip
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.policy import Bot


def legs(world, stats, count, vertical, skip):
    routes = []
    for prism, box in world.prisms:
        x0, y0, x1, y1 = box
        if prism['kind'] == 'bridge' or not 8 < x1-x0 < 45 or not 10 < y1-y0 < 50:
            continue
        x,y = (x0+x1)/2,(y0+y1)/2
        start,end = ([x,y1+14],[x,y0-18]) if vertical else ([x0-14,y],[x1+18,y])
        start.append(world.ground(*start))
        end.append(world.ground(*end))
        if (not world.walkable(start,start,stats) or not world.walkable(end,end,stats)
                or world.walkable(start,end,stats)):
            continue
        if skip:
            skip -= 1
            continue
        routes.append((start,end))
        if len(routes) == count:
            break
    return routes


def advance(world, me, action):
    dt = .05
    for _ in range(2):
        stats = me['stats']
        speed = stats['boost_speed' if action['boost'] else 'walk_speed']
        delta = [speed*action['move'][k]-me['vel'][k] for k in range(2)]
        factor = min(1., stats['ground_accel']*dt/max(1e-9,math.hypot(*delta)))
        vel = [me['vel'][k]+factor*delta[k] for k in range(2)]
        x,y = [me['pos'][k]+dt*vel[k] for k in range(2)]
        end = [x,y,world.ground(x,y)]
        if world.walkable(me['pos'],end,stats):
            me['pos'],me['vel'] = end,[*vel,0]
        else:
            me['vel'] = [0,0,0]
        if action['boost']:
            me['energy'] = max(0,me['energy']-dt*stats['boost_drain'])


def main():
    kit = ROOT/'official/mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as stream:
        hello = json.loads(next(stream))
        frame = next(m for line in stream if (m:=json.loads(line))['type']=='obs')
    hello['map']['dir'] = str(kit/'arena')
    for key in ('mechs','projectiles','events','sounds','pickups','cubes','drops','crates','beams'):
        frame[key] = []
    world = Bot(hello).world
    results = []
    timings = []
    for start,end in legs(world,frame['self']['stats'],12,'--vertical' in sys.argv,12 if '--holdout' in sys.argv else 0):
        bot = Bot(hello)
        if '--direct' in sys.argv:
            bot.zone_route.waypoint = lambda situation, goal: goal
        me = frame['self']
        me.update(pos=start[:],vel=[0,0,0],energy=100,grounded=True,in_zone=False)
        frame['zone'] = dict(center=end[:2],next_center=end[:2],radius=9,next_radius=9,
                             shrink_start=0,shrink_end=80,dps=20)
        for i in range(140):
            frame.update(t=i*.1,tick=i*2)
            begin = time.perf_counter()
            action = bot.act(frame)
            timings.append((time.perf_counter()-begin)*1000)
            advance(world,me,action)
            if math.dist(me['pos'][:2],end[:2]) < 9:
                break
        results.append(round((i+1)*.1,1) if math.dist(me['pos'][:2],end[:2]) < 9 else None)
    print(json.dumps(dict(routes=len(results),reached=sum(t is not None for t in results),arrival_s=results,
                          p99_ms=round(sorted(timings)[int(.99*len(timings))],2),max_ms=round(max(timings),2))))


if __name__ == '__main__':
    main()
