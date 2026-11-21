"""[CODEX_ENHANCEMENT_2026-11-21] EXP-011 recorded-input audit only."""
import gzip,json,subprocess,sys,time,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agent.policy import Bot
BASELINE='581009b54f2331846ff52d0d553e15e400248baa'


def baseline_class():
    pkg=types.ModuleType('magazine_baseline');pkg.__path__=[];sys.modules[pkg.__name__]=pkg
    for name in ('world','observation','strategy','navigation','combat','policy'):
        m=types.ModuleType('magazine_baseline.'+name);sys.modules[m.__name__]=m
        source=subprocess.check_output(['git','show',f'{BASELINE}:agent/{name}.py'],cwd=ROOT).decode()
        exec(compile(source,f'{BASELINE}:agent/{name}.py','exec'),m.__dict__)
    return sys.modules['magazine_baseline.policy'].Bot


def main():
    kit=ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f:messages=[json.loads(l) for l in f]
    h=messages[0];h['map']['dir']=str(kit/'arena');old,new=baseline_class()(h),Bot(h)
    times=[];changes=0;offers=0
    for o in messages:
        if o['type']!='obs':continue
        a=old.act(o);t=time.perf_counter();b=new.act(o);times.append((time.perf_counter()-t)*1000)
        assert {k:v for k,v in a.items() if k!='pick'}=={k:v for k,v in b.items() if k!='pick'}
        changes += a.get('pick')!=b.get('pick');offers += bool(o.get('offer'))
    v=sorted(times)
    r=dict(experiment='EXP-011',kind='input audit; not a match simulator',baseline_commit=BASELINE,baseline_official_score=2.38,
           observations=len(v),upgrade_offer_observations=offers,changed_picks=changes,other_action_changes=0,
           candidate_ms=dict(p50=v[len(v)//2],p99=v[int(.99*len(v))],maximum=max(v)),official_score=None)
    (ROOT/'reports'/'EXP-011-replay.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))


if __name__=='__main__':main()
