"""[CODEX_ENHANCEMENT_2026-11-21] EXP-005 input A/B against official 2.19."""
import gzip
import json
from pathlib import Path
import subprocess
import sys
import time
import types

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agent.policy import Bot
BASELINE='28afe8bcba8480f7483dc65280afdc270c0120ac'


def baseline_class():
    package=types.ModuleType('best_agent');package.__path__=[];sys.modules['best_agent']=package
    for name in ('world','observation','strategy','navigation','combat','policy'):
        m=types.ModuleType('best_agent.'+name);sys.modules[m.__name__]=m
        s=subprocess.check_output(['git','show',f'{BASELINE}:agent/{name}.py'],cwd=ROOT).decode()
        exec(compile(s,f'{BASELINE}:agent/{name}.py','exec'),m.__dict__)
    return sys.modules['best_agent.policy'].Bot


def main():
    kit=ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f: messages=[json.loads(l) for l in f]
    h=messages[0];h['map']['dir']=str(kit/'arena');a,b=baseline_class()(h),Bot(h)
    times=[];changed=0
    for o in messages:
        if o['type']!='obs': continue
        old=a.act(o);t=time.perf_counter();new=b.act(o);times.append((time.perf_counter()-t)*1000)
        assert {k:v for k,v in old.items() if k not in ('move','boost')}=={k:v for k,v in new.items() if k not in ('move','boost')}
        changed += old!=new
    values=sorted(times)
    result=dict(experiment='EXP-005',kind='recorded-input A/B; NOT simulation',baseline_commit=BASELINE,baseline_official_score=2.19,
                observations=len(values),changed_movement_decisions=changed,non_movement_changes=0,
                candidate_ms=dict(p50=values[len(values)//2],p99=values[int(.99*len(values))],maximum=max(values)),official_score=None)
    (ROOT/'reports'/'EXP-005-replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__': main()
