"""[ASTRA_ENHANCEMENT_2026-11-21] Score causal horizontal motion predictions in the starter recording."""
import gzip
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from motion_forecast import MotionHistory


def main():
    kit = ROOT/'official/mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f:
        hello = json.loads(next(f))
        frames = [o for row in f if (o:=json.loads(row))['type']=='obs']
    config = hello['config']
    motion = MotionHistory(config['mech'])
    errors = {}
    for i,obs in enumerate(frames):
        enemies = [m for m in obs['mechs'] if m['kind']=='mech']
        motion.observe(obs['t'],enemies)
        for e in enemies:
            flight = math.dist(e['pos'],obs['self']['pos'])/config['weapons']['gun']['speed']
            due = obs['t']+flight
            # Freeze each prediction before reading its label from subsequent observations.
            forecasts = [e['vel'],motion.velocity(e,flight)]
            prev = obs
            for later in frames[i+1:]:
                if later['t']-prev['t']>.15:
                    break
                a = next((m for m in prev['mechs'] if m['id']==e['id']),None)
                b = next((m for m in later['mechs'] if m['id']==e['id']),None)
                if not a or not b:
                    break
                if later['t'] >= due:
                    f = (due-prev['t'])/(later['t']-prev['t'])
                    truth = [a['pos'][k]+f*(b['pos'][k]-a['pos'][k]) for k in (0,1)]
                    group = 'early' if obs['t']<=18 else 'late'
                    for tag,v in zip(('constant','history'),forecasts):
                        pred = [e['pos'][k]+v[k]*flight for k in (0,1)]
                        errors.setdefault((group,tag),[]).append(math.dist(pred,truth))
                    break
                prev=later
    for group,values in errors.items():
        print(*group,len(values),round(sum(values)/len(values),3),
              sum(err<=config['mech']['radius'] for err in values))


if __name__=='__main__':
    main()
