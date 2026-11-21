"""[CODEX_ENHANCEMENT_2026-11-21] EXP-009 input audit; not game scoring."""
import gzip,json,subprocess,sys,time,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agent.policy import Bot
BASELINE='2f30e3d217461379eedebeea49751b6209397c79'


def baseline_class():
    package=types.ModuleType('attention_baseline');package.__path__=[];sys.modules[package.__name__]=package
    for name in ('world','observation','strategy','navigation','combat','policy'):
        m=types.ModuleType('attention_baseline.'+name);sys.modules[m.__name__]=m
        source=subprocess.check_output(['git','show',f'{BASELINE}:agent/{name}.py'],cwd=ROOT).decode()
        exec(compile(source,f'{BASELINE}:agent/{name}.py','exec'),m.__dict__)
    return sys.modules['attention_baseline.policy'].Bot


def main():
    kit=ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f:messages=[json.loads(l) for l in f]
    h=messages[0];h['map']['dir']=str(kit/'arena');old,new=baseline_class()(h),Bot(h)
    timings=[];changed=0
    for o in messages:
        if o['type']!='obs':continue
        a=old.act(o);t=time.perf_counter();b=new.act(o);timings.append((time.perf_counter()-t)*1000)
        assert {k:v for k,v in a.items() if k!='aim'}=={k:v for k,v in b.items() if k!='aim'}
        changed += a['aim']!=b['aim']
    v=sorted(timings)
    result=dict(experiment='EXP-009',kind='input replay; not a match simulation',baseline_commit=BASELINE,baseline_official_score=2.25,
                observations=len(v),changed_aim_decisions=changed,other_action_changes=0,
                candidate_ms=dict(p50=v[len(v)//2],p99=v[int(.99*len(v))],maximum=max(v)),official_score=None)
    (ROOT/'reports'/'EXP-009-replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
