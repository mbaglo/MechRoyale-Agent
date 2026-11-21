"""[CODEX_ENHANCEMENT_2026-11-21] EXP-004 input audit; not a simulation."""
import gzip
import json
from pathlib import Path
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agent.policy import Bot

BASELINE='8a87e8a467dde525d25fcf9cb5181087c6e55fd7'


def baseline_class():
    package=types.ModuleType('v1_agent');package.__path__=[];sys.modules['v1_agent']=package
    for name in ('world','observation','strategy','navigation','combat','policy'):
        module=types.ModuleType('v1_agent.'+name);sys.modules[module.__name__]=module
        source=subprocess.check_output(['git','show',f'{BASELINE}:agent/{name}.py'],cwd=ROOT).decode()
        exec(compile(source,f'{BASELINE}:agent/{name}.py','exec'),module.__dict__)
    return sys.modules['v1_agent.policy'].Bot


def main():
    kit=ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f: messages=[json.loads(l) for l in f]
    hello=messages[0];hello['map']['dir']=str(kit/'arena')
    original,candidate=baseline_class()(hello),Bot(hello)
    goal_changes,action_changes=0,0;timings=[]
    for o in messages:
        if o['type']!='obs': continue
        a=original.act(o);start=time.perf_counter();b=candidate.act(o);timings.append((time.perf_counter()-start)*1000)
        assert {k:v for k,v in a.items() if k not in ('move','boost')} == {k:v for k,v in b.items() if k not in ('move','boost')}
        goal_changes += original.strategy.goal(original.observer.parse(o),original.mode)!=candidate.strategy.goal(candidate.observer.parse(o),candidate.mode)
        action_changes += a!=b
    v=sorted(timings)
    r=dict(experiment='EXP-004',kind='recorded-input audit; NOT gameplay simulation',baseline_commit=BASELINE,
           changed_parameter=dict(weapon_search_radius_m=dict(baseline=65,candidate=130)),
           observations=len(v),changed_goals=goal_changes,changed_actions=action_changes,non_movement_action_changes=0,
           candidate_ms=dict(p50=v[len(v)//2],p99=v[int(.99*len(v))],maximum=max(v)),official_score=None)
    (ROOT/'reports'/'EXP-004-replay.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))


if __name__=='__main__': main()
