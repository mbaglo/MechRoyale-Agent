"""[ASTRA_ENHANCEMENT_2026-11-21] Compare ground positions against fixed recorded laser cues."""
import gzip
import copy
import json
from pathlib import Path

from probe_zone_routes import Bot, advance


def probe(hello, frames, paired):
    bot=Bot(hello)
    if not paired:
        bot.laser_duel.goal=lambda s:None
    previous=None
    launches=shielded=sight=seen=0
    for o in frames:
        observed=o['self']
        if previous is None or o['t']-previous>.15:
            me=dict(observed,pos=observed['pos'][:],vel=observed['vel'][:])
            since=0
        else:
            me=dict(observed,pos=me['pos'],vel=me['vel'],energy=me['energy'])
        previous=o['t']
        obs=dict(o,self=me)
        command=bot.act(obs)
        for opponent in (e for e in o['mechs'] if e['kind']=='mech' and 'laser' in e.get('weapons',())):
            seen+=1
            ep=opponent['pos']
            h=1+.05*opponent.get('cubes',0)
            origin=[*ep[:2],ep[2]+7*h]
            pos=me['pos']
            sight+=bot.world.clear([*pos[:2],pos[2]+me['stats']['muzzle_height']],
                                   [*ep[:2],ep[2]+4.5*h])
            if any(b['kind']=='laser' and b['by']==opponent['id'] for b in o.get('beams',[])):
                launches+=1
                shielded+=bot.laser_duel.sheltered(origin,pos,me['stats'])
        since=advance(bot.world,me,command,since,True)
    return dict(contact_ticks=seen,firing_lanes=sight,observed_releases=launches,sheltered_on_release=shielded)


def fixed_cycle(hello, start, paired):
    bot=Bot(hello)
    if not paired:
        bot.laser_duel.goal=lambda s:None
    o=copy.deepcopy(start)
    e=next(e for e in o['mechs'] if e['kind']=='mech')
    stat=hello['config']['weapons']['laser']
    o.update(events=[],projectiles=[],sounds=[])
    me=o['self']
    muzzle=[*e['pos'][:2],e['pos'][2]+7*(1+.05*e.get('cubes',0))]
    body=[*e['pos'][:2],e['pos'][2]+4.5*(1+.05*e.get('cubes',0))]
    since=0
    lanes=0
    for n in range(round((stat['cooldown']+stat['charge'])*10)+1):
        elapsed=n*.1
        o['t']=start['t']+elapsed
        e['charging']=elapsed>=stat['cooldown']
        o['beams']=[] if n else [dict(kind='laser',by=e['id'],age=0,path=[muzzle,muzzle])]
        a=bot.act(o)
        pos=me['pos']
        if elapsed<=1:
            lanes+=bot.world.clear([*pos[:2],pos[2]+me['stats']['muzzle_height']],body)
        if elapsed+.01>=stat['cooldown']+stat['charge']:
            return bot.laser_duel.sheltered(muzzle,pos,me['stats']),lanes
        since=advance(bot.world,me,a,since,True)


if __name__=='__main__':
    kit=Path(__file__).resolve().parents[1]/'official/mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f:
        hello=json.loads(next(f))
        frames=[o for row in f if (o:=json.loads(row))['type']=='obs']
    hello['map']['dir']=str(kit/'arena')
    for mode in (False,True):
        print('paired' if mode else 'parent',probe(hello,frames,mode))
    for mode in (False,True):
        cases=[fixed_cycle(hello,o,mode) for o in frames[::10] if len(o['mechs'])==1 and o['mechs'][0].get('kind')=='mech']
        print('static source cycle',mode,'cases',len(cases),'shielded',sum(s for s,_ in cases),
              'first second lanes',sum(l for _,l in cases))
