"""NES P1 synthetic pixel/event and conservative SNES schedule experiment.
SPDX-License-Identifier: MIT
No ROM input. Not a NES PPU, SNES emulator, or board timing signoff.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from dataclasses import dataclass
from pathlib import Path

W,H=256,240
class Fault(ValueError): pass

def tile_pixel(bank, tile, x, y, generation=0):
    return ((x ^ y ^ tile ^ (bank*3) ^ generation) + (x//3) + (y//2)) & 3

def planar(bank,tile,generation):
    out=bytearray()
    for y in range(8):
        row=[tile_pixel(bank,tile,x,y,generation) for x in range(8)]
        out.extend(sum(((p>>b)&1)<<(7-x) for x,p in enumerate(row)) for b in (0,1))
    return bytes(out)

@dataclass(frozen=True)
class Event:
    y:int
    x:int
    kind:str
    value:int
    window:int=0

@dataclass
class Scene:
    name:str
    frame:int
    events:list[Event]
    sprites:list[dict]


def scenes():
    result=[]
    for frame in (0,1,255,256):
        result.append(Scene('scroll_split_'+str(frame),frame,[Event(117,0,'scroll',0)],[]))
    result.append(Scene('eight_banks',3,[Event(73+i*13,0,'bank',i+8,i) for i in range(8)],[]))
    result.append(Scene('chr_generation',4,[Event(103,0,'generation',1)],[]))
    result.append(Scene('palette_emphasis',5,[Event(49,0,'palette',9),Event(101,0,'emphasis',5),Event(173,0,'grey',1)],[]))
    result.append(Scene('dot_palette',6,[Event(119,123,'palette',17)],[]))
    sprites=[dict(x=24+i*7,y=81,height=8 if i%2 else 16,tile=i,bank=i%8,behind=i%3==0) for i in range(10)]
    result.append(Scene('sprite_selection',7,[],sprites))
    result.append(Scene('left_mask_blank',8,[Event(0,0,'mask',1),Event(87,0,'blank',1),Event(93,0,'blank',0)],sprites))
    return result


def state_at(scene,y,x, line_only=False):
    s=dict(scroll=scene.frame,banks=list(range(8)),generation=0,palette=0,emphasis=0,grey=0,mask=0,blank=0)
    for e in scene.events:
        # Deliberately restricted hardware candidate: midline writes apply next line.
        pos=(e.y+(1 if line_only and e.x else 0),0 if line_only else e.x)
        if pos>(y,x): continue
        if e.kind=='bank': s['banks'][e.window]=e.value
        else:s[e.kind]=e.value
    return s


def reference(scene, line_only=False, sprite_limit=8):
    pixels=[]
    for y in range(H):
        active=[sp for sp in scene.sprites if sp['y']<=y<sp['y']+sp['height']][:sprite_limit]
        for x in range(W):
            s=state_at(scene,y,x,line_only)
            sx=(x+s['scroll'])%512; tx=sx//8; ty=y//8
            bank=s['banks'][(tx+ty)%8]; tile=(tx+ty*7)%64
            bg=tile_pixel(bank,tile,sx%8,y%8,s['generation'])
            if s['mask'] and x<8:bg=0
            c=(bg+4*((tx//2+ty//2)%4)+s['palette'])%64 if bg else 0
            for sp in active:
                if sp['x']<=x<sp['x']+8 and not(s['mask'] and x<8):
                    sy=y-sp['y']; st=(sp['tile']&~1)+(sy//8) if sp['height']==16 else sp['tile']
                    p=tile_pixel(sp['bank'],st,x-sp['x'],sy%8)
                    if p:
                        if not(sp['behind'] and bg): c=(32+p+(sp['tile']%4)*4+s['palette'])%64
                        break
            if s['blank']: c=0
            if s['grey']: c &= 0x30
            pixels.append(c | (s['emphasis']<<6))
    return pixels


def capture(scene):
    """Resolved tile runs + line sprite decisions, not final pixel copies.
    Events here describe synthetic effective state, NOT raw $2005/$2006 writes.
    """
    if len(scene.events)>64:raise Fault('EVENT_OVERFLOW')
    if scene.events!=sorted(scene.events,key=lambda e:(e.y,e.x)):raise Fault('EVENT_ORDER')
    for e in scene.events:
        if not(0<=e.x<W and 0<=e.y<H):raise Fault('EVENT_RANGE')
        if e.kind not in ('scroll','bank','generation','palette','emphasis','grey','mask','blank'):raise Fault('EVENT_KIND')
        if e.kind=='bank' and not 0<=e.window<8:raise Fault('BANK_WINDOW')
    atlas={}; lines=[]
    def key(bank,tile,gen,role):
        k=f'{bank*1024+tile*16}:{gen}:{role}'
        atlas.setdefault(k,planar(bank,tile,gen).hex())
        return k
    for y in range(H):
        runs=[]; x=0
        while x<W:
            s=state_at(scene,y,x); sx=(x+s['scroll'])%512; tx=sx//8;ty=y//8
            end=min(W,x+8-sx%8)
            end=min([end]+[e.x for e in scene.events if e.y==y and x<e.x<end])
            runs.append(dict(x=x,end=end,key=key(s['banks'][(tx+ty)%8],(tx+ty*7)%64,s['generation'],'bg'),fine=sx%8,row=y%8,pal=(tx//2+ty//2)%4,state={k:s[k] for k in ('palette','emphasis','grey','mask','blank')}))
            x=end
        sprites=[]
        for sp in [sp for sp in scene.sprites if sp['y']<=y<sp['y']+sp['height']][:8]:
            sy=y-sp['y'];t=(sp['tile']&~1)+sy//8 if sp['height']==16 else sp['tile']
            sprites.append(dict(x=sp['x'],key=key(sp['bank'],t,0,'obj'),row=sy%8,behind=sp['behind'],pal=sp['tile']%4))
        lines.append(dict(runs=runs,sprites=sprites))
    return dict(schema=1,frame_id=scene.frame,epoch=0,name=scene.name,atlas=atlas,lines=lines)


def replay(packet, stale=False):
    tiles={k:bytes.fromhex(v) for k,v in packet['atlas'].items()}
    if stale:
        for k in list(tiles):
            address,gen,role=k.split(':');old=f'{address}:0:{role}'
            if gen!='0' and old in tiles:tiles[k]=tiles[old]
    def sample(k,x,y):
        raw=tiles[k];return ((raw[y*2]>>(7-x))&1)|(((raw[y*2+1]>>(7-x))&1)<<1)
    pixels=[]
    for line in packet['lines']:
        for r in line['runs']:
            s=r['state']
            for x in range(r['x'],r['end']):
                bg=sample(r['key'],r['fine']+x-r['x'],r['row'])
                if s['mask'] and x<8:bg=0
                c=(bg+4*r['pal']+s['palette'])%64 if bg else 0
                for sp in line['sprites']:
                    if sp['x']<=x<sp['x']+8 and not(s['mask'] and x<8):
                        p=sample(sp['key'],x-sp['x'],sp['row'])
                        if p:
                            if not(sp['behind'] and bg):c=(32+p+sp['pal']*4+s['palette'])%64
                            break
                if s['blank']:c=0
                if s['grey']:c &= 0x30
                pixels.append(c|(s['emphasis']<<6))
    return pixels


def diff(a,b):
    if len(a)!=len(b):raise Fault('PIXEL_LENGTH')
    indices=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    return dict(different_pixels=len(indices),first_xy=[indices[0]%W,indices[0]//W] if indices else None)


def patch_lower_bound(a,b):
    """Count exact reference tiles covering differences; NOT a hardware compiler.
    Palette feasibility checks include emphasis in the symbolic color identity.
    Bytes exclude whole-mode conversion, resident background, mapping and bus cost.
    """
    changed={(i%W//8,i//W//8) for i,(x,y) in enumerate(zip(a,b)) if x!=y}
    color_sets=[]
    for tx,ty in sorted(changed):
        color_sets.append(set(a[(ty*8+dy)*W+tx*8+dx] for dy in range(8) for dx in range(8)))
    return dict(tiles=len(changed),tile_bytes_4bpp=len(changed)*32,tilemap_bytes=len(changed)*2,
                max_colors_per_tile=max(map(len,color_sets),default=0),
                individually_4bpp_encodable=all(len(c)<=16 for c in color_sets),
                individually_mode0_2bpp_encodable=all(len(c)<=4 for c in color_sets),
                cgram_bytes_without_palette_sharing=sum(len(c)*2 for c in color_sets),
                palette_groups_without_sharing=len(color_sets),
                full_mode_conversion_cost_included=False,hardware_schedule_proven=False)


class Mailbox:
    """Two immutable frame slots. Errors stop the experiment, never discard silently."""
    def __init__(self):self.epoch=0;self.slots=[None,None];self.last=-1;self.peak=0
    def publish(self,frame,complete=True):
        if not complete:raise Fault('INCOMPLETE_FRAME')
        if frame<=self.last:raise Fault('FRAME_ORDER')
        if None not in self.slots:raise Fault('QUEUE_FULL')
        self.last=frame;i=self.slots.index(None);self.slots[i]=(self.epoch,frame,'READY')
        self.peak=max(self.peak,sum(s is not None for s in self.slots));return self.epoch,frame,i
    def take(self,t):
        ep,f,i=t
        if ep!=self.epoch:raise Fault('STALE_EPOCH')
        if self.slots[i]!=(ep,f,'READY'):raise Fault('OWNER')
        ready=[s[1] for s in self.slots if s and s[2]=='READY']
        if f!=min(ready):raise Fault('CONSUME_ORDER')
        self.slots[i]=(ep,f,'READING')
    def ack(self,t):
        ep,f,i=t
        if ep!=self.epoch:raise Fault('STALE_EPOCH')
        if self.slots[i]!=(ep,f,'READING'):raise Fault('OWNER')
        self.slots[i]=None
    def reset(self):self.epoch+=1;self.slots=[None,None];self.last=-1


class TileCache:
    """Bounded slot model; keys include physical address, generation and role."""
    def __init__(self,capacity):self.capacity=capacity;self.slots={};self.owners={};self.peak=0
    def acquire(self,token,keys):
        if token in self.owners:raise Fault('CACHE_OWNER')
        keys=set(keys)
        pinned=set().union(*self.owners.values()) if self.owners else set()
        missing=keys-self.slots.keys()
        evictable=set(self.slots)-pinned-keys
        needed=max(0,len(self.slots)+len(missing)-self.capacity)
        if needed>len(evictable):raise Fault('CACHE_PINNED_FULL')
        for k in sorted(evictable)[:needed]:del self.slots[k]
        free=iter(sorted(set(range(self.capacity))-set(self.slots.values())))
        for k in sorted(missing):self.slots[k]=next(free)
        self.owners[token]=keys;self.peak=max(self.peak,len(self.slots))
        return len(missing)
    def release(self,token):
        if token not in self.owners:raise Fault('CACHE_OWNER')
        del self.owners[token]


def schedule(payload,height,channels=5,hdma_bytes=4,hdma_channels=2,diagnostic=False):
    # conservative explicitly assumed CPU reserve; not measured board timing.
    blank=(261-height)*1324-4  # worst odd-frame short line
    reserve=768+(256 if diagnostic else 0)
    setup=channels*192
    dma=payload*8+channels*24+16
    hdma_init=18+hdma_channels*24
    used=reserve+setup+dma+hdma_init
    line_cost=18+hdma_channels*16+hdma_bytes*8
    return dict(height=height,payload_bytes=payload,blank_master_clocks=blank,cpu_reserve=reserve,
                setup_master_clocks=setup,dma_master_clocks=dma,hdma_init_master_clocks=hdma_init,
                used_master_clocks=used,margin_master_clocks=blank-used,deadline_pass=used<=blank,
                target_80_percent_pass=used*5<=blank*4,hdma_line_master_clocks=line_cost,
                hdma_channels=hdma_channels,hdma_line_pass=hdma_channels<=8 and line_cost<=272,
                diagnostic=diagnostic,board_measured=False)


def negative_tests():
    out=[]
    def rejects(name,code,fn):
        try:fn()
        except Fault as e:
            if str(e)!=code:raise AssertionError((name,str(e),code))
            out.append(dict(name=name,detected=code));return
        raise AssertionError('undetected '+name)
    m=Mailbox();t=m.publish(0);m.take(t);m.publish(1)
    rejects('slow_consumer','QUEUE_FULL',lambda:m.publish(2))
    rejects('double_take','OWNER',lambda:m.take(t))
    m.reset();rejects('reset_during_dma_ack','STALE_EPOCH',lambda:m.ack(t))
    t=m.publish(0);m.take(t);m.ack(t)
    rejects('duplicate_ack','OWNER',lambda:m.ack(t))
    rejects('old_frame','FRAME_ORDER',lambda:m.publish(0))
    rejects('incomplete','INCOMPLETE_FRAME',lambda:m.publish(1,False))
    m=Mailbox();m.publish(0);t=m.publish(1)
    rejects('out_of_order_consumer','CONSUME_ORDER',lambda:m.take(t))
    rejects('event_overflow','EVENT_OVERFLOW',lambda:capture(Scene('bad',0,[Event(0,0,'scroll',0)]*65,[])))
    rejects('event_order','EVENT_ORDER',lambda:capture(Scene('bad',0,[Event(2,0,'scroll',0),Event(1,0,'scroll',0)],[])))
    rejects('event_dot_range','EVENT_RANGE',lambda:capture(Scene('bad',0,[Event(0,256,'scroll',0)],[])))
    rejects('event_kind','EVENT_KIND',lambda:capture(Scene('bad',0,[Event(0,0,'unsupported',0)],[])))
    rejects('bank_window','BANK_WINDOW',lambda:capture(Scene('bad',0,[Event(0,0,'bank',0,8)],[])))
    cache=TileCache(2);old=(0x20000,0,'bg');new=(0x20000,1,'bg')
    assert cache.acquire((0,0),[old,(0x20010,0,'bg')])==2
    before=dict(cache.slots)
    rejects('pinned_generation_eviction','CACHE_PINNED_FULL',lambda:cache.acquire((0,1),[new]))
    assert cache.slots==before and (0,1) not in cache.owners
    cache.release((0,0));assert cache.acquire((0,1),[new])==1
    rejects('stale_cache_release','CACHE_OWNER',lambda:cache.release((0,0)))
    rejects('cache_single_frame_overflow','CACHE_PINNED_FULL',lambda:cache.acquire((0,2),[(i,0,'bg') for i in range(3)]))
    m=Mailbox()
    for f in range(1000):
        t=m.publish(f);m.take(t);m.ack(t)
    out.append(dict(name='1000_ordered_frames',peak_depth=m.peak,remaining=sum(s is not None for s in m.slots)))
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    results=[]
    for scene in scenes():
        packet=capture(scene);reference_pixels=reference(scene);b=replay(packet)
        match=diff(reference_pixels,b);assert match['different_pixels']==0,(scene.name,match)
        atlas=packet['atlas'];bg=sum(k.endswith(':bg') for k in atlas);obj=len(atlas)-bg
        # Resolved map storage is measured separately: this is NOT yet a hardware encoder.
        raw_runs=sum(len(l['runs']) for l in packet['lines'])
        r=dict(name=scene.name,frame_id=scene.frame,events=len(scene.events),ab=match,
               synthetic_reference_sha256=hashlib.sha256(struct.pack('<'+'H'*len(b),*b)).hexdigest(),
               bg_cache_misses_cold=bg,obj_cache_misses_cold=obj,chr_upload_bytes=bg*16+obj*32,
               resolved_runs=raw_runs,resolved_runs_bytes_at_16_each=raw_runs*16,
               native_candidate=diff(reference_pixels,reference(scene,line_only=True,sprite_limit=32)),
               patch_lower_bound=patch_lower_bound(reference_pixels,reference(scene,line_only=True,sprite_limit=32)),
               visible_loss={str(h):dict(rows=H-h,pixels=W*(H-h),first_xy=[0,h]) for h in (224,239)})
        if scene.name=='chr_generation':
            r['stale_generation_injection']=diff(reference_pixels,replay(packet,stale=True))
            assert r['stale_generation_injection']['different_pixels']>0
        if scene.name in ('dot_palette','sprite_selection'):
            assert r['native_candidate']['different_pixels']>0
        (a.out/(scene.name+'.json')).write_text(json.dumps(packet,separators=(',',':')),encoding='utf-8')
        results.append(r)
    payloads={'warm_example':128+544+64,'64_bg_64_obj_example':64*16+64*32+128+544+64,
              '8k_both_roles':8192+16384+128+544+64,'full_4bpp':30720,
              'one_4bpp_patch_row':32*32+64+544+64,'16_patch_rows':16*32*32+1024+544+64,'observed_patch_standalone':544+34+128}
    budgets={n:[schedule(b,h,channels=6 if n=='observed_patch_standalone' else 5,diagnostic=d) for h in (224,239) for d in (False,True)] for n,b in payloads.items()}
    assert all(not x['deadline_pass'] for x in budgets['full_4bpp'])
    result=dict(candidate='NES-P1-001',scope='synthetic A/B only; native_candidate is a restricted software approximation, NOT C',
                patterns=results,negative_tests=negative_tests(),budgets=budgets,
                hardware_eligible=False,commercial_rom_access=False,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(patterns=len(results),ab_differences=sum(r['ab']['different_pixels'] for r in results),
                         native_failures={r['name']:r['native_candidate'] for r in results if r['native_candidate']['different_pixels']},
                         negative_tests=len(result['negative_tests'])),indent=2))
if __name__=='__main__':main()
