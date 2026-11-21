"""[CODEX_ENHANCEMENT_2026-11-21] EXP-010 exact-baseline input audit."""
import gzip,json,subprocess,sys,time,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agent.policy import Bot
BASELINE='644baa44fe773c5e2429bec5c715f91787770ab1'


def baseline_class():
    pkg=types.ModuleType('cube_baseline');pkg.__path__=[];sys.modules[pkg.__name__]=pkg
    for name in ('world','observation','strategy','navigation','combat','policy'):
        m=types.ModuleType('cube_baseline.'+name);sys.modules[m.__name__]=m
        source=subprocess.check_output(['git','show',f'{BASELINE}:agent/{name}.py'],cwd=ROOT).decode()
        exec(compile(source,f'{BASELINE}:agent/{name}.py','exec'),m.__dict__)
    return sys.modules['cube_baseline.policy'].Bot


def main():
    kit=ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f:messages=[json.loads(l) for l in f]
    h=messages[0];h['map']['dir']=str(kit/'arena');old,new=baseline_class()(h),Bot(h)
    samples=[];changed=0
    for o in messages:
        if o['type']!='obs':continue
        a=old.act(o);start=time.perf_counter();b=new.act(o);samples.append((time.perf_counter()-start)*1000)
        assert {k:v for k,v in a.items() if k not in ('move','boost')}=={k:v for k,v in b.items() if k not in ('move','boost')}
        changed += a!=b
    v=sorted(samples)
    result=dict(experiment='EXP-010',kind='recorded-input audit; not gameplay',baseline_commit=BASELINE,baseline_official_score=2.31,
                parameter=dict(cube_search_radius_m=dict(baseline=55,candidate=130)),observations=len(v),changed_actions=changed,
                non_movement_changes=0,candidate_ms=dict(p50=v[len(v)//2],p99=v[int(.99*len(v))],maximum=max(v)),official_score=None)
    (ROOT/'reports'/'EXP-010-replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
