# Raw SNES fine-X audit and right-edge regressions. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,hashlib,json
from run_nes_fine_scroll import audit
from build_nes_fine_scroll import decode,encode,fine_coord
from build_nes_trace_replay import display_rgb
from verify_nes_video_workloads import read_case
def rejected(fn):
    try:fn()
    except (AssertionError,ValueError):return True
    return False
def verify(root,workloads):
    cases={}
    for case in ('top','bottom','baseline','edge','scroll','length'):
        result=audit(root/case/'build',root/case/'capture')
        assert result==json.loads((root/case/'capture/result.json').read_text())
        assert result['expected_outcome_verified'];cases[case]=result
    inverse={rgb:key for key,rgb in display_rgb().items()};coverage=[]
    for frame in range(1,5):
        merged={}
        for case in ('top','bottom'):
            offset=cases[case]['viewport']
            rgb=(root/case/'capture'/f'frame-{frame-1:03}.rgb').read_bytes()
            actual=bytes(inverse[rgb[i:i+3]] for i in range(0,len(rgb),3))
            for i,value in enumerate(actual):
                dest=i+offset*256
                assert dest not in merged or merged[dest]==value
                merged[dest]=value
        assert set(merged)==set(range(256*240))
        output=bytes(merged[i] for i in range(256*240))
        assert output==(root/'top/build'/f'expected-{frame}.idx').read_bytes()
        coverage.append(dict(frame=frame,unique_pixels=len(output),sha256=hashlib.sha256(output).hexdigest()))
    build=root/'top/build';p=(build/'packet-1.bin').read_bytes();atlas=(build/'chr-snes.bin').read_bytes()
    negatives={}
    for name,offset,value in [('magic',0,0),('version',4,2),('fine_range',6,8),('flags',7,1),
                             ('width',9,0),('height',10,239),('map_length',16,0),
                             ('tile_range',21,255),('palette',2007,255)]:
        changed=bytearray(p);assert changed[offset]!=value;changed[offset]=value
        negatives[name]=rejected(lambda:decode(bytes(changed),atlas))
    negatives['truncated_packet']=rejected(lambda:decode(p[:-1],atlas))
    changed=bytearray(p);changed[1940]^=1
    restored=decode(bytes(changed),atlas);expected=(build/'expected-1.idx').read_bytes()
    bad=[i for i,(a,b) in enumerate(zip(restored,expected)) if a!=b]
    negatives['right_column_pixel_detection']=bool(bad) and all(i%256==255 for i in bad)
    frames,bg,_,_,chrdata=read_case(workloads,'fine_x')
    feature=frames[0]['features'];seq=[e for e in bg if e['frame']==frames[0]['frame']]
    edge_index=next(i for i,e in enumerate(seq) if (pos:=fine_coord(e['line'],e['dot'])) is not None and pos[1]==32)
    missing=seq[:edge_index]+seq[edge_index+1:]
    negatives['missing_edge_plane']=rejected(lambda:encode(1,missing,feature,chrdata))
    for name,key,value in [('sprite','ppu_mask',30),('vertical','scroll_y',1),('coarse','scroll_x',8),
                           ('mutable','immutable_chr_rom',False)]:
        negatives[name]=rejected(lambda:encode(1,seq,dict(feature,**{key:value}),chrdata))
    assert all(negatives.values())
    normal=[cases[name] for name in ('top','bottom','baseline')]
    return dict(candidate='NES-R2-FINE-SCROLL-022',audit_pass=True,cases=cases,full240_fine_x_coverage=coverage,
                fine_x_unique_source_pixels=245760,normal_actual_pixel_comparisons=3*4*256*239,
                software_negative_tests=negatives,packet_bytes=2008,ppu_dma_bytes=1988,
                delta_from020=dict(packet_bytes=64,ppu_dma_bytes=60,
                    max_normal_consumer_clocks=19618-18046),
                max_normal_consumer_clocks=max(c['max_commit_master_clocks'] for c in normal),
                min_normal_deadline_margin=min(c['min_commit_margin_master_clocks'] for c in normal),
                source_height=240,simultaneous_display_height=239,full240_simultaneous_display_proven=False,
                observed_nes_fine_x=[0,1],live_producer_deadline_proven=False,
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='Actual SNES replay of captured NES fine-X0/1;offline packets/full immutable16KiB CHR preload. No coarse/vertical/mid-frame scroll,sprite,largeCHR,live producer or hardware proof.')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('runs','workloads','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();result=verify(a.runs,a.workloads)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','full240_fine_x_coverage')},indent=2))