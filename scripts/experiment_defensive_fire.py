"""[CODEX_ENHANCEMENT_2026-11-21] EXP-003 recorded-input A/B audit, not a game."""
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

BASELINE = '8a87e8a467dde525d25fcf9cb5181087c6e55fd7'


def load_baseline():
    package = types.ModuleType('v1_agent')
    package.__path__ = []
    sys.modules['v1_agent'] = package
    for name in ('world','observation','strategy','navigation','combat','policy'):
        module = types.ModuleType('v1_agent.'+name)
        sys.modules[module.__name__] = module
        source = subprocess.check_output(['git','show',f'{BASELINE}:agent/{name}.py'],cwd=ROOT).decode()
        exec(compile(source,f'{BASELINE}:agent/{name}.py','exec'),module.__dict__)
    return sys.modules['v1_agent.policy'].Bot


def main():
    kit = ROOT/'official'/'mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f:
        messages = [json.loads(line) for line in f]
    messages[0]['map']['dir'] = str(kit/'arena')
    baseline,candidate = load_baseline()(messages[0]),Bot(messages[0])
    times,changed,additional = [],0,0
    for obs in messages:
        if obs['type']!='obs':
            continue
        original = baseline.act(obs)
        start = time.perf_counter()
        action = candidate.act(obs)
        times.append((time.perf_counter()-start)*1000)
        # Abort the experiment if it changes anything except gun trigger output.
        assert {k:v for k,v in action.items() if k!='fire'} == {k:v for k,v in original.items() if k!='fire'}
        for slot,weapon in enumerate(obs['self']['weapons']):
            if not weapon or weapon['kind']!='gun':
                assert action['fire'][slot] == original['fire'][slot]
        changed += action != original
        additional += any(a and not b for a,b in zip(action['fire'],original['fire']))
    values = sorted(times)
    result = dict(experiment='EXP-003',kind='recorded-input audit; NOT gameplay simulation',baseline_commit=BASELINE,
                  observations=len(times),changed_actions=changed,additional_gun_trigger_decisions=additional,
                  non_gun_action_changes=0,candidate_ms=dict(p50=values[len(values)//2],p99=values[int(.99*len(values))],maximum=max(values)),
                  official_score=None,official_status='not submitted',submission_id=None)
    (ROOT/'reports'/'EXP-003-replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
