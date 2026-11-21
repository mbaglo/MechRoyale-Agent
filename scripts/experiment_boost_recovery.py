"""[CODEX_ENHANCEMENT_2026-11-21] EXP-007 exact-source replay A/B."""
import gzip,json,subprocess,sys,time,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agent.policy import Bot
BASELINE='2f30e3d217461379eedebeea49751b6209397c79'


def baseline_class():
    pkg=types.ModuleType('best_agent');pkg.__path__=[];sys.modules['best_agent']=pkg
    for name in ('world','observation','strategy','navigation','combat','policy'):
        module=types.ModuleType('best_agent.'+name);sys.modules[module.__name__]=module
        source=subprocess.check_output(['git','show',f'{BASELINE}:agent/{name}.py'],cwd=ROOT).decode()
        exec(compile(source,f'{BASELINE}:agent/{name}.py','exec'),module.__dict__)
    return sys.modules['best_agent.policy'].Bot


def main():
    kit=ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f: messages=[json.loads(l) for l in f]
    h=messages[0];h['map']['dir']=str(kit/'arena');a,b=baseline_class()(h),Bot(h)
    timings=[];changes=0
    for o in messages:
        if o['type']!='obs':continue
        old=a.act(o);start=time.perf_counter();new=b.act(o);timings.append((time.perf_counter()-start)*1000)
        assert {k:v for k,v in old.items() if k!='boost'}=={k:v for k,v in new.items() if k!='boost'}
        changes += old['boost']!=new['boost']
    v=sorted(timings)
    result=dict(experiment='EXP-007',baseline_commit=BASELINE,baseline_official_score=2.25,kind='input replay; not a match simulator',
                observations=len(v),changed_boost_decisions=changes,other_action_changes=0,
                candidate_ms=dict(p50=v[len(v)//2],p99=v[int(.99*len(v))],maximum=max(v)),official_score=None)
    (ROOT/'reports'/'EXP-007-replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
