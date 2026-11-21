"""[CODEX_ENHANCEMENT_2026-11-21] EXP-008 bounded roof-refuge behavior.

Geometry/energy feasibility is approximate. Actual physics remains authoritative.
"""
import math
from .world import inside


class RoofRefuge:
    def __init__(self,world):
        self.world=world
        self.sites=[]
        self.target=None
        self.phase=None
        self.started=0.
        self.retry_at=0.
        for prism,box in world.prisms:
            if prism['kind']!='building':continue
            for u in (.25,.5,.75):
                for v in (.25,.5,.75):
                    x,y=box[0]+u*(box[2]-box[0]),box[1]+v*(box[3]-box[1])
                    if 10<=prism['top']-world.ground(x,y)<=36 and self.supported(x,y,prism,5.5):
                        self.sites.append((x,y,prism['top'],prism))

    @staticmethod
    def supported(x,y,p,radius):
        for i in range(8):
            a=i*math.pi/4
            xx,yy=x+radius*math.cos(a),y+radius*math.sin(a)
            if not inside(xx,yy,p['ring']) or any(inside(xx,yy,h) for h in p.get('holes',[])):
                return False
        return inside(x,y,p['ring']) and not any(inside(x,y,h) for h in p.get('holes',[]))

    def vertical_clear(self,pos,top,stats):
        r,h=stats.get('radius',2.5),stats.get('height',9)
        n=max(1,math.ceil((top+h+1-pos[2])/.8))
        for i in range(n+1):
            z=pos[2]+.2+(top+h+1-pos[2])*i/n
            if any(self.world.solid(pos[0]+dx,pos[1]+dy,z)
                   for dx,dy in ((0,0),(r,0),(-r,0),(0,r),(0,-r))):
                return False
        return True

    @staticmethod
    def launch_point(pos,p,radius):
        nearest=None
        ring=p['ring'];ax,ay=ring[-2:]
        for i in range(0,len(ring),2):
            bx,by=ring[i:i+2];dx,dy=bx-ax,by-ay
            t=max(0,min(1,((pos[0]-ax)*dx+(pos[1]-ay)*dy)/max(1e-9,dx*dx+dy*dy)))
            ex,ey=ax+t*dx,ay+t*dy;d=math.hypot(pos[0]-ex,pos[1]-ey)
            if d>.01 and (nearest is None or d<nearest[0]):
                nearest=(d,ex,ey)
            ax,ay=bx,by
        if nearest is None:return None
        d,x,y=nearest
        return [x+(pos[0]-x)/d*(radius+2),y+(pos[1]-y)/d*(radius+2)]

    def choose(self,s):
        me,z=s.me,s.obs['zone'];pos,st=me['pos'],me['stats']
        r=st.get('radius',2.5)
        ranked=[]
        for site in self.sites:
            x,y,top,p=site;rise=top-pos[2];distance=math.dist(pos[:2],(x,y))
            if not (8<rise<=30 and distance<=65 and math.dist((x,y),z['next_center'])<z['next_radius']-18):continue
            if not self.supported(x,y,p,r+3):continue
            launch=self.launch_point(pos,p,r)
            if launch is None or inside(*launch,p['ring']):continue
            launch=[*launch,self.world.ground(*launch)]
            walk=math.dist(pos[:2],launch[:2])/max(1,st['walk_speed'])
            climb=rise/max(1,st.get('max_rise_speed',10))
            traverse=math.dist(launch[:2],(x,y))/max(1,st['walk_speed']*.55)
            # Delay and landing margin, without assuming recharge while jetting.
            need=(climb+traverse+.8)*st.get('jet_drain',15)
            if need>me['energy']-12 or s.obs['t']+walk+climb+traverse+15>z['shrink_end']:continue
            ranked.append((distance+rise,[x,y,top],p,launch))
        # Bound expensive checks to three candidates and two enemy rays per site.
        choices=[]
        for score,point,p,launch in sorted(ranked,key=lambda x:x[0])[:3]:
            if not self.world.walkable(pos,launch,st):continue
            if not self.vertical_clear(launch,point[2]+1,st):continue
            a=[launch[0],launch[1],point[2]+1]
            if not self.world.clear(a,[point[0],point[1],point[2]+1]):continue
            if not self.world.clear([a[0],a[1],a[2]+st.get('height',9)],
                                    [point[0],point[1],point[2]+1+st.get('height',9)]):continue
            for e in s.enemies[:2]:
                if self.world.clear([e['pos'][0],e['pos'][1],e['pos'][2]+7],
                                    [point[0],point[1],point[2]+4.5]):score+=25
            choices.append((score,dict(point=point,prism=p,launch=launch)))
        return min(choices,key=lambda x:x[0])[1] if choices else None

    def abort(self,t):
        self.target=None;self.phase=None;self.retry_at=t+5

    def goal(self,s,original):
        me,o=s.me,s.obs;t=o['t'];pos=me['pos'];z=o['zone']
        if self.target:
            point=self.target['point']
            hostile_roof=any(abs(e['pos'][2]-point[2])<5 and math.dist(e['pos'][:2],pos[:2])<35 for e in s.enemies)
            if s.urgent or not me['in_zone'] or hostile_roof or math.dist(point[:2],z['next_center'])>=z['next_radius']-10:
                self.abort(t)
            elif self.phase!='hold' and (t-self.started>18 or me['energy']<10):
                self.abort(t)
        if self.target is None and t>=self.retry_at and not s.urgent and me['grounded'] and me['energy']>=85:
            close=[e for e in s.enemies if math.dist(e['pos'],pos)<160]
            if (len(close)>=2 or (s.health<.5 and close)) and pos[2]-self.world.ground(*pos[:2])<2:
                self.target=self.choose(s);self.retry_at=t+5
                if self.target:self.phase='approach';self.started=t
        if self.target is None:return original
        point,launch=self.target['point'],self.target['launch']
        if self.phase=='approach' and math.dist(pos[:2],launch[:2])<1.5 and math.hypot(*me['vel'][:2])<2:
            if not self.vertical_clear(pos,point[2]+1,me['stats']):
                self.abort(t);return original
            self.phase='climb'
        if self.phase=='climb' and me['grounded'] and abs(pos[2]-point[2])<2:
            self.phase='hold'
        if self.phase=='hold' and (pos[2]<point[2]-3):
            self.abort(t);return original
        return launch[:2] if self.phase=='approach' else point[:2]

    def apply(self,s,action):
        if self.target is None:return action
        # [CODEX_ENHANCEMENT_2026-11-21] Save jet energy on approach; quiet
        # refuge behavior avoids resetting health regen with outgoing damage.
        action.update(boost=False,jump=False,fire=[False,False])
        if self.phase=='climb':
            pos=s.me['pos'];point=self.target['point'];r=s.me['stats'].get('radius',2.5)
            if pos[2]<point[2]+.8:
                action.update(move=[0.,0.],boost=True,jump=s.me['grounded'])
            else:
                dx,dy=point[0]-pos[0],point[1]-pos[1];d=math.hypot(dx,dy)
                move=[dx/max(1,d)*.55,dy/max(1,d)*.55] if d>1.5 else [0.,0.]
                supported=self.supported(pos[0],pos[1],self.target['prism'],r)
                action.update(move=move,boost=not supported)
        elif self.phase=='hold' and math.dist(s.me['pos'][:2],self.target['point'][:2])<3:
            action['move']=[0.,0.]
        return action
