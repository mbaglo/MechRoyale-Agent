"""[CODEX_ENHANCEMENT_2026-11-21] Reproducible input-only baseline comparison.

Loads the preserved baseline from Git objects without a checkout or repository
mutation. Neither recorded nor synthetic inputs produce gameplay scores.
"""
import copy
import gzip
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agent.policy import Bot

BASELINE = '8a87e8a467dde525d25fcf9cb5181087c6e55fd7'


def baseline_class():
    package = types.ModuleType('baseline_agent')
    package.__path__ = []
    sys.modules[package.__name__] = package
    for name in ('world','observation','strategy','navigation','combat','policy'):
        module = types.ModuleType('baseline_agent.'+name)
        sys.modules[module.__name__] = module
        source = subprocess.check_output(['git','show',f'{BASELINE}:agent/{name}.py'],cwd=ROOT).decode()
        exec(compile(source,f'{BASELINE}:agent/{name}.py','exec'),module.__dict__)
    return sys.modules['baseline_agent.policy'].Bot


def inputs():
    kit = ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f:
        messages = [json.loads(line) for line in f]
    hello = messages[0]
    hello['map']['dir'] = str(kit/'arena')
    return hello,[m for m in messages if m['type']=='obs']


def crowded(observation, frames=60):
    o = copy.deepcopy(observation)
    p = o['self']['pos']
    o['self'].update(hp=400,energy=40,grounded=True,in_zone=True)
    o.update(crates=[],pickups=[],cubes=[],drops=[],sounds=[],events=[],offer=None)
    o['zone'].update(center=p[:2],next_center=p[:2],radius=140,next_radius=70,shrink_start=250,shrink_end=280)
    o['mechs'] = []
    for i in range(15):
        angle = i*2*math.pi/15
        d = 30+i*7
        o['mechs'].append(dict(id=(o['self']['id']+i+1)%16,kind='mech',
                              pos=[p[0]+math.cos(angle)*d,p[1]+math.sin(angle)*d,p[2]],
                              vel=[-math.cos(angle)*10,-math.sin(angle)*10,0],aim=[angle+math.pi,0],
                              hp=1000,max_hp=1400,weapons=['gun','laser'],charging=True))
    o['projectiles'] = [dict(id=i,kind='gun',pos=[p[0]+math.cos(i)*40,p[1]+math.sin(i)*40,p[2]+4.5],
                            vel=[-math.cos(i)*100,-math.sin(i)*100,0]) for i in range(16)]
    return [dict(o,t=200+i*.1,tick=4000+i*2) for i in range(frames)]


def measure(cls, hello, observations, rounds=3):
    timings, boost, firing, modes = [],0,0,{}
    routes = 0
    for _ in range(rounds):
        bot = cls(hello)
        for obs in observations:
            start = time.perf_counter()
            action = bot.act(obs)
            timings.append((time.perf_counter()-start)*1000)
            boost += bool(action['boost'])
            firing += any(action['fire'])
            modes[bot.mode] = modes.get(bot.mode,0)+1
            routes += bool(getattr(getattr(bot.navigator,'router',None),'path',None))
    values = sorted(timings)
    return dict(decisions=len(values),decision_ms=dict(mean=statistics.mean(values),p50=statistics.median(values),
                                                     p99=values[int(.99*len(values))],maximum=max(values)),
                boost_fraction=boost/len(values),firing_fraction=firing/len(values),modes=modes,decisions_with_route=routes)


def main():
    hello,observations = inputs()
    baseline = baseline_class()
    result = dict(kind='recorded and synthetic input comparison; NOT gameplay simulation',
                  baseline_commit=BASELINE,baseline_official_score=dict(score=2.10,submission='BB-6CB32C3E',source='user supplied'),
                  candidate_official_score=None,target_official_score_above=3.0,
                  recorded={},crowded={})
    for label,cls in [('baseline',baseline),('candidate',Bot)]:
        result['recorded'][label] = measure(cls,hello,observations)
        result['crowded'][label] = measure(cls,hello,crowded(observations[0]))
    path = ROOT/'reports'/'optimization-comparison.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
