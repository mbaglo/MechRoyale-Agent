"""[CODEX_ENHANCEMENT_2026-11-21] EXP-008 input audit; no simulated outcomes."""
import gzip,json,subprocess,sys,time,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agent.policy import Bot
BASELINE='2f30e3d217461379eedebeea49751b6209397c79'


def baseline_class():
    pkg=types.ModuleType('roof_baseline');pkg.__path__=[];sys.modules[pkg.__name__]=pkg
    for name in ('world','observation','strategy','navigation','combat','policy'):
        m=types.ModuleType('roof_baseline.'+name);sys.modules[m.__name__]=m
        source=subprocess.check_output(['git','show',f'{BASELINE}:agent/{name}.py'],cwd=ROOT).decode()
        exec(compile(source,f'{BASELINE}:agent/{name}.py','exec'),m.__dict__)
    return sys.modules['roof_baseline.policy'].Bot


def main():
    kit=ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f: messages=[json.loads(l) for l in f]
    h=messages[0];h['map']['dir']=str(kit/'arena');old,new=baseline_class()(h),Bot(h)
    samples=[];changed=0;phases={}
    for o in messages:
        if o['type']!='obs':continue
        original=old.act(o);start=time.perf_counter();action=new.act(o);samples.append((time.perf_counter()-start)*1000)
        assert original['tick']==action['tick'] and original['aim']==action['aim']
        changed += original!=action
        phase=new.roof.phase or 'baseline';phases[phase]=phases.get(phase,0)+1
    values=sorted(samples)
    result=dict(experiment='EXP-008',kind='recorded observations; not a game simulation',baseline_commit=BASELINE,baseline_official_score=2.25,
                observations=len(values),changed_actions=changed,roof_sites=len(new.roof.sites),phases=phases,
                candidate_ms=dict(p50=values[len(values)//2],p99=values[int(.99*len(values))],maximum=max(values)),official_score=None)
    (ROOT/'reports'/'EXP-008-replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
