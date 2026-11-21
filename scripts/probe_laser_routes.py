"""[ASTRA_ENHANCEMENT_2026-11-21] Test ground routes during the kit's recorded charge warnings."""
import copy
import gzip
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.policy import Bot


def step(world, me, move, boost):
    stats = me['stats']
    speed = stats['boost_speed' if boost else 'walk_speed']
    dt = .05
    desired = [v * speed for v in move]
    for _ in range(2):
        change = [desired[k] - me['vel'][k] for k in range(2)]
        fraction = min(1., stats['ground_accel']*dt / max(1e-6, math.hypot(*change)))
        velocity = [me['vel'][k] + fraction*change[k] for k in range(2)]
        x, y = [me['pos'][k] + dt*velocity[k] for k in range(2)]
        end = [x, y, world.ground(x,y)]
        if world.walkable(me['pos'], end, stats):
            me['pos'], me['vel'] = end, [*velocity, 0.]
        else:
            me['vel'] = [0.,0.,0.]


def probe(hello, frames, use_cover):
    bot = Bot(hello)
    if not use_cover:
        bot.laser_cover.goal = lambda s: None
    me = copy.deepcopy(frames[0]['self'])
    concealed = 0
    for frame in frames:
        obs = dict(frame, self=me)
        action = bot.act(obs)
        step(bot.world, me, action['move'], action['boost'])
        shooter = next(m for m in frame['mechs'] if m.get('charging'))
        x,y,z = shooter['pos']
        size = 1 + shooter.get('cubes',0) * hello['config']['cubes']['size_per_cube']
        source = [x,y,z + size*hello['config']['mech']['muzzle_height']]
        x,y,z = me['pos']
        hidden = all(not bot.world.clear(source,[x,y,z + f*me['stats']['height']]) for f in (.5,.95))
        concealed += hidden
    return dict(steps=len(frames), covered_steps=concealed, covered_at_last_step=hidden)


def main():
    kit = ROOT / 'official/mechfight-kit'
    with gzip.open(kit / 'check/stream.jsonl.gz', 'rt') as f:
        hello = json.loads(next(f))
        windows = []
        for line in f:
            frame = json.loads(line)
            if frame['type'] != 'obs' or not any(m.get('charging') for m in frame['mechs']):
                continue
            if not windows or frame['t'] - windows[-1][-1]['t'] > .11:
                windows.append([])
            windows[-1].append(frame)
    hello['map']['dir'] = str(kit / 'arena')
    print(json.dumps([dict(start=w[0]['t'], baseline=probe(hello,w,False), candidate=probe(hello,w,True))
                      for w in windows], indent=2))


if __name__ == '__main__':
    main()
