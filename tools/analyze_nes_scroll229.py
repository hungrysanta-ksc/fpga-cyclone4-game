# SPDX-License-Identifier: MIT
"""Measure real-game emulator observations without treating them as FPGA packets.

Snapshot deltas and PPU write journals are different views, not additive costs.
BG tag reuse excludes attributes/raster/OBJ and is not a deployment saving.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, hashlib, json, statistics, struct
from run_nes_scroll229 import ROM_SHA

FETCH = struct.Struct('<IhHHBIHHH7B')
WRITE = struct.Struct('<BIhHHB')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def records(path, codec):
    data = path.read_bytes()
    assert len(data) % codec.size == 0, (path.name, 'truncated record')
    return codec.iter_unpack(data)

def summary(values):
    v=sorted(values); assert v
    return dict(mean=statistics.mean(v), median=statistics.median(v),
                p95=v[min(len(v)-1,(len(v)*95+99)//100-1)], minimum=v[0], maximum=v[-1])

def delta(a,b):
    assert len(a)==len(b)
    changed=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    runs=[]
    for i in changed:
        if runs and runs[-1][0]+runs[-1][1]==i and runs[-1][1]<255:
            runs[-1][1]+=1
        else:runs.append([i,1])
    # An explicit accounting model only: offset16+length8 per contiguous span.
    # No epoch/header/CRC/ACK, no deployed codec, no renderer equivalence claim.
    return dict(changed=len(changed),spans=len(runs),span_body_bytes=len(changed)+3*len(runs))

def main():
    p=argparse.ArgumentParser()
    for n in ('capture','control','rom','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args(); assert sha(a.rom)==ROM_SHA
    meta=json.loads((a.capture/'capture.json').read_text());assert meta['exit_code']==0
    control=json.loads((a.control/'capture.json').read_text());assert control['exit_code']==0
    for k in ['rom_sha256','script_sha256','runner_sha256','emulator_sha256','core_sha256']:
        assert meta[k]==control[k],k
    assert (a.capture/'frames.tsv').read_bytes()==(a.control/'frames.tsv').read_bytes(), 'input/clock trace differs'
    first,last=meta['capture_first'],meta['capture_last'];ids=list(range(first,last+1))
    raw=a.rom.read_bytes();prg=raw[4]*16384;trainer=512 if raw[6]&4 else 0
    chrdata=raw[16+trainer+prg:]; assert len(chrdata)==131072
    fetchcount=Counter();phases=Counter();source_types=Counter();tags=defaultdict(set)
    bg=defaultdict(dict);bg_v=defaultdict(dict);scroll=defaultdict(list)
    bank_pages=defaultdict(lambda:defaultdict(set))
    # Preserve physical identity and both plane rows. Never infer ROM-bank
    # identity from screen-space tile numbers or from the frame-end bank map.
    for row in records(a.capture/'ppu-fetch.bin',FETCH):
        f,line,dot,addr,value,physical,kind,v,t,x,mask,ctrl,oy,ot,oa,ox=row
        assert first<=f<=last and kind==57 and 0<=physical<len(chrdata)
        assert chrdata[physical]==value,'captured CHR byte differs from user ROM'
        fetchcount[f]+=1;source_types[kind]+=1;phases[dot%8]+=1;tags[f].add(physical//16)
        bank_pages[f][addr//1024].add(physical//1024)
        pre=321<=dot<=336
        if not (pre or 1<=dot<=256):continue
        target=line+1 if pre else line
        col=(0 if dot<329 else 1) if pre else ((dot+7)//8+1)
        if not (8<=target<232 and col<=32 and dot%8 in (5,7)):continue
        key=(target-8,col,dot%8)
        assert key not in bg[f],(f,key,'duplicate phase')
        bg[f][key]=(physical//16,physical%16)
        bg_v[f][key]=(v&0xfff,physical%16)
        if target==32 and col==2 and dot%8==5:scroll[f].append(((v&31)|((v>>5)&32))*8+x)
    assert sorted(fetchcount)==ids
    writecount={f:Counter() for f in ids};changed_writes=Counter();trailing_writes=0;mask_changes=defaultdict(list)
    register_writes=defaultdict(Counter);mapper_writes=defaultdict(Counter)
    for kind,f,line,dot,addr,value in records(a.capture/'writes.bin',WRITE):
        assert kind<4 and first<=f<=last+1
        # Mesen advances frameCount after endFrame, before the next startFrame.
        # The startFrame capture gate includes trailing VBlank for last+1 and
        # excludes leading VBlank for first. Preserve raw data, summarize only
        # complete write-frame labels first+1..last; never relabel the events.
        if f==last+1:
            assert line>=240
            trailing_writes+=1
            continue
        writecount[f][kind]+=1
        if kind==0:register_writes[f][addr]+=1
        if kind==1:mapper_writes[f][addr]+=1
        if kind==0 and addr==0x2001:mask_changes[f].append([line,dot,value])
        if kind==2 and f>first:changed_writes['nametable' if 0x2000<=addr<0x3f00 else 'palette' if addr>=0x3f00 else 'chr']+=1
    frames=[];previous=None;previous_world={};conflicts=0;checks=0;rgb_pins={}
    for f in ids:
        before=(a.capture/f'state-{f-1:04d}.bin').read_bytes()
        now=(a.capture/f'state-{f:04d}.bin').read_bytes()
        assert len(before)==len(now)==2384
        rgb=a.capture/f'frame-{f:04d}.rgb';assert rgb.stat().st_size==256*240*3
        rgb_pins[str(f)]=sha(rgb)
        ctrl=a.control/rgb.name
        if ctrl.exists():assert rgb.read_bytes()==ctrl.read_bytes(),('observation changed visible result',f);checks+=1
        segments={n:delta(before[lo:hi],now[lo:hi]) for n,lo,hi in
                  [('nametable',0,2048),('oam',2048,2304),('palette',2304,2336),('bank_end_state',2336,2384)]}
        row_counts=Counter(k[0]+8 for k in bg[f])
        missing_rows=[[y,66-row_counts[y]] for y in range(8,232) if row_counts[y]!=66]
        for y,missing in missing_rows:
            assert missing>0 and any(0<=y-line<=1 and (value&0x18)!=0x18 for line,dot,value in mask_changes[f]),(f,y,'missing fetch without observed mask change')
        byworld={};bad=set()
        for k,val in bg[f].items():
            key=bg_v[f][k]
            if key in byworld and byworld[key]!=val:bad.add(key)
            byworld[key]=val
        for k in bad:byworld.pop(k,None)
        conflicts+=len(bad)
        same=sum(previous.get(k)==v for k,v in bg[f].items()) if previous is not None else None
        reused=sum(previous_world.get(bg_v[f][k])==v for k,v in bg[f].items()) if previous is not None else None
        frames.append(dict(frame=f,fetches=fetchcount[f],physical_chr_tiles=len(tags[f]),snapshot=segments,
                           write_events={str(k):writecount[f][k] for k in range(4)},
                           mask_changes=mask_changes[f],missing_bg_fetch_rows=missing_rows,
                           bg_plane_cells=len(bg[f]),same_screen_tag_cells=same,
                           previous_v_key_tag_cells=reused,ambiguous_v_keys=len(bad),scroll_x_row32=scroll[f],
                           multiple_physical_banks_in_frame={str(p):sorted(v) for p,v in bank_pages[f].items() if len(v)>1},
                           cpu_ppu_register_writes={hex(k):v for k,v in sorted(register_writes[f].items())},
                           mapper_register_writes={hex(k):v for k,v in sorted(mapper_writes[f].items())}))
        previous=bg[f];previous_world=byworld
    assert checks>=3
    sections={n:{metric:summary([f['snapshot'][n][metric] for f in frames]) for metric in ['changed','spans','span_body_bytes']}
              for n in ['nametable','oam','palette','bank_end_state']}
    names=['ppu_register','mapper_register','ppu_memory','oam_dma']
    # A deliberately bounded workload, selected by observed motion, not by
    # labeling every first-level frame as scrolling. The sample column carries
    # a +16-pixel fetch offset; only differences are camera displacement.
    assert (first,last)==(880,975), 'This workload contract pins frames 880..975'
    assert all(f['scroll_x_row32']==[16] for f in frames[:26])
    assert all(frames[i]['scroll_x_row32'][0]>frames[i-1]['scroll_x_row32'][0] for i in range(26,96))
    windows={}
    for name,lo,hi in [('stationary_camera',881,905),('continuous_scroll',906,975)]:
        ff=[f for f in frames if lo<=f['frame']<=hi]
        previous_x=frames[lo-first-1]['scroll_x_row32'][0]
        windows[name]=dict(first=lo,last=hi,frames=len(ff),
            camera_displacement=ff[-1]['scroll_x_row32'][0]-previous_x,
            changed_bytes={n:summary([f['snapshot'][n]['changed'] for f in ff]) for n in sections},
            snapshot_span_model_bytes=summary([sum(f['snapshot'][n]['span_body_bytes'] for n in ['nametable','oam','palette']) for f in ff]),
            screen_tag_equal_fraction=statistics.mean(f['same_screen_tag_cells']/f['bg_plane_cells'] for f in ff),
            v_key_tag_equal_fraction=statistics.mean(f['previous_v_key_tag_cells']/f['bg_plane_cells'] for f in ff),
            frames_with_bank_switch=len([f for f in ff if f['multiple_physical_banks_in_frame']]),
            frames_with_mask_disable=len([f for f in ff if any((v&0x18)!=0x18 for l,d,v in f['mask_changes'])]),
            write_events={n:summary([f['write_events'][str(k)] for f in ff]) for k,n in enumerate(names)},
            cpu_ppu_register_writes=dict(sum((Counter(f['cpu_ppu_register_writes']) for f in ff),Counter())),
            mapper_register_writes=dict(sum((Counter(f['mapper_register_writes']) for f in ff),Counter())))
    result=dict(passed=True,scope=__doc__,rom_sha256=ROM_SHA,emulator=meta,
                frames=frames,frame_count=len(frames),physical=False,deployed_geometry=False,
                source_checks=dict(chr_reads=sum(fetchcount.values()),chr_values_exact=True,
                                   expected_full_bg_plane_cells=224*33*2,actual_bg_plane_cells=summary([f['bg_plane_cells'] for f in frames]),fetch_mod8=dict(phases),
                                   missing_bg_rows_have_observed_mask_disable=True,
                                   observational_rgb_matches=checks,ambiguous_v_keys=conflicts),
                snapshot_summary=sections,write_event_summary={n:summary([writecount[f][k] for f in ids[1:]]) for k,n in enumerate(names)},
                write_window=dict(complete_frame_labels=[first+1,last],first_label_partial=True,trailing_vblank_excluded=trailing_writes),
                ppu_write_counts=dict(changed_writes),
                workload_windows=windows,
                bg_tag_comparison=dict(screen_equal_fraction=statistics.mean(f['same_screen_tag_cells']/f['bg_plane_cells'] for f in frames[1:]),
                                       v_key_equal_fraction=statistics.mean(f['previous_v_key_tag_cells']/f['bg_plane_cells'] for f in frames[1:])),
                limitations=['Mesen PPU observations, not production FPGA collector query images or actual ARM/sink packets.',
                             'End-frame state deltas do not preserve intermediate writes, mapper latches, raster effects or displayed pixels by themselves.',
                             'Tag comparison excludes attributes, palettes, OBJ, publication and decoder cost; it is not a cache hit-rate or FPS prediction.',
                             'Snapshot span accounting excludes headers/control and may require more source state than available FPGA/ARM memory.',
                             'Only frames906..975 scroll continuously; frames880..905 have a stationary camera. This is 70 scrolling frames, not a long-run or all-mapper guarantee.',
                             'CPU2004 writes include OAM DMA and CPU2007 overlaps PPU-memory writes. These views must not be summed as independent transfer costs.'],
                inputs={n:sha(a.capture/n) for n in ['capture.json','ppu-fetch.bin','writes.bin','frames.tsv','capture.lua']},
                rgb_sha256=rgb_pins,analyzer_sha256=sha(Path(__file__)))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['passed','frame_count','source_checks','workload_windows']},indent=2))

if __name__=='__main__':main()
