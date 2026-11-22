"""[ASTRA_ENHANCEMENT_2026-11-21] Probe two-contact mode decisions on sampled official geometry."""
import gzip
import json
import math
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agent.policy import Bot


def main():
    kit=ROOT/'official/mechfight-kit'
    with gzip.open(kit/'check'/'stream.jsonl.gz','rt') as f:
        h=json.loads(next(f))
        o=next(q for row in f if (q:=json.loads(row))['type']=='obs')
    h['map']['dir']=str(kit/'arena')
    bot=Bot(h)
    world=bot.world
    me=o['self']
    me.update(in_zone=True,energy=100,hp=1250,max_hp=1400)
    me['weapons'][0].update(ammo=12,cooldown=0,reload=0)
    for group in ('mechs','projectiles','crates','cubes','pickups','drops','events','sounds','beams'):
        o[group]=[]
    cases=changed=flanks=0
    timings=[]
    for x,y in ((270,-259),(45,-73),(-82,89),(-199,-205),(130,120),(345,60),(-310,130)):
        p=[x,y,world.ground(x,y)]
        if not world.walkable(p,p,me['stats']):
            continue
        me['pos']=p
        o['zone'].update(center=[x,y],next_center=[x,y],radius=300,next_radius=200,shrink_end=100)
        for i in range(12):
            es=[]
            for angle,dist,hp,ident in ((i*math.pi/6,66,130,3),((i+4)*math.pi/6,86,1300,5)):
                a,b=x+dist*math.cos(angle),y+dist*math.sin(angle)
                pos=[a,b,world.ground(a,b)]
                if not world.walkable(pos,pos,me['stats']):
                    break
                es.append(dict(id=ident,kind='mech',pos=pos,vel=[0,0,0],aim=[angle+math.pi,0],
                               hp=hp,max_hp=1400,cubes=0,weapons=['gun']))
            if len(es)!=2:
                continue
            cases+=1
            o.update(t=10+cases*.1,mechs=es)
            me['aim']=[i*math.pi/6,0]
            start=time.perf_counter()
            bot.act(o)
            timings.append((time.perf_counter()-start)*1000)
            if bot.mode!='balanced':
                continue
            changed+=1
            # Test more approach bearings than the live controller can afford.
            rival=es[1]['pos']
            actual=False
            flight=math.dist(es[0]['pos'],p)/me['weapons'][0]['stats']['speed']
            horizon=(.15+flight+2*me['weapons'][0]['stats']['cooldown'])*h['config']['mech']['boost_speed']
            for radius in (horizon/3,2*horizon/3,horizon):
                for j in range(24):
                    a,b=rival[0]+radius*math.cos(j*math.pi/12),rival[1]+radius*math.sin(j*math.pi/12)
                    site=[a,b,world.ground(a,b)]
                    if world.walkable(rival,site,me['stats']) and any(world.clear([a,b,site[2]+7],
                              [x,y,p[2]+k*me['stats']['height']]) for k in (.5,.95)):
                        actual=True
                        break
                if actual:
                    break
            flanks+=actual
    print(dict(cases=cases,balanced=changed,denser_sample_found_exposed_flank=flanks,
               max_decision_ms=round(max(timings),2)))


if __name__=='__main__':
    main()
