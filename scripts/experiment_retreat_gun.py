"""[CODEX_ENHANCEMENT_2026-11-21] EXP-012 input A/B; not a match simulator."""
import gzip,json,subprocess,sys,time,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agent.policy import Bot
BASELINE='644baa44fe773c5e2429bec5c715f91787770ab1'


def baseline_class():
    pkg=types.ModuleType('retreat_baseline');pkg.__path__=[];sys.modules[pkg.__name__]=pkg
    for name in ('world','observation','strategy','navigation','combat','policy'):
        m=types.ModuleType('retreat_baseline.'+name);sys.modules[m.__name__]=m
        source=subprocess.check_output(['git','show',f'{BASELINE}:agent/{name}.py'],cwd=ROOT).decode()
        exec(compile(source,f'{BASELINE}:agent/{name}.py','exec'),m.__dict__)
    return sys.modules['retreat_baseline.policy'].Bot


def main():
    kit=ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f:messages=[json.loads(l) for l in f]
    h=messages[0];h['map']['dir']=str(kit/'arena');old,new=baseline_class()(h),Bot(h)
    samples=[];changes=0
    for o in messages:
        if o['type']!='obs':continue
        a=old.act(o);t=time.perf_counter();b=new.act(o);samples.append((time.perf_counter()-t)*1000)
        assert {k:v for k,v in a.items() if k!='fire'}=={k:v for k,v in b.items() if k!='fire'}
        for i,w in enumerate(o['self']['weapons']):
            if not w or w['kind']!='gun':assert a['fire'][i]==b['fire'][i]
        changes+=a['fire']!=b['fire']
    v=sorted(samples)
    r=dict(experiment='EXP-012',kind='input replay only; not gameplay',baseline_commit=BASELINE,baseline_official_score=2.31,
           observations=len(v),changed_gun_fire_decisions=changes,other_action_changes=0,
           candidate_ms=dict(p50=v[len(v)//2],p99=v[int(.99*len(v))],maximum=max(v)),official_score=None)
    (ROOT/'reports'/'EXP-012-replay.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))


if __name__=='__main__':main()
