# Native one-sprite replay and evidence audit. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,json,hashlib
from run_nes_sprite_replay import audit
from nes_sprite_packet import decode,sprite_state
from build_nes_trace_replay import display_rgb
from verify_nes_video_workloads import read_case
def rejected(fn):
    try:fn()
    except (AssertionError,ValueError):return True
    return False
def verify(root,workloads):
    cases={}
    for case in ('top','bottom','fine_x','hide','obj','count'):
        result=audit(root/case/'build',root/case/'capture')
        assert result==json.loads((root/case/'capture/result.json').read_text())
        assert result['expected_outcome_verified'];cases[case]=result
    inverse={v:k for k,v in display_rgb().items()};coverage=[]
    for f in range(1,5):
        pixels={}
        for case in ('top','bottom'):
            rgb=(root/case/'capture'/f'frame-{f-1:03}.rgb').read_bytes()
            indexed=bytes(inverse[rgb[j:j+3]] for j in range(0,len(rgb),3))
            for i,v in enumerate(indexed):
                pos=i+cases[case]['viewport']*256
                assert pos not in pixels or pixels[pos]==v
                pixels[pos]=v
        assert set(pixels)==set(range(256*240))
        output=bytes(pixels[i] for i in range(256*240))
        assert output==(root/'top/build'/f'expected-{f}.idx').read_bytes()
        coverage.append(dict(frame=f,unique_pixels=len(output),indexed_sha256=hashlib.sha256(output).hexdigest()))
    frames,bg,reads,_,chrdata=read_case(workloads,'sprite')
    source=[]
    for i,info in enumerate(frames,1):
        state,data,oam=sprite_state(workloads/'sprite/capture',info['frame'],reads,chrdata,'sprite')
        p=(root/'top/build'/f'packet-{i}.bin').read_bytes()
        assert state['source_oam']==[79,1,0,40] and state['physical_tile']==257
        assert p[2008:2040]==data and p[2048:2052]==oam
        assert len(state['fetches'])==16
        source.append(dict(frame=i,nes_frame=info['frame'],physical_tile=257,read_bytes=16,
                           nes_oam=state['source_oam'],snes_oam=list(oam)))
    build=root/'top/build';p=(build/'packet-1.bin').read_bytes();atlas=(build/'chr-snes.bin').read_bytes()
    tests={}
    for name,off,value in [('magic',0,0),('count_range',7,2),('count_hides_without_oam',7,0),
       ('fine_range',6,8),('map_length',16,0),('obj_upper_plane',2024,1),
       ('obj_palette',2042,0),('obj_tile',2050,1),('obj_priority',2051,0),
       ('clipped_x',2048,249),('clipped_y',2049,233)]:
        q=bytearray(p);assert q[off]!=value;q[off]=value
        tests[name]=rejected(lambda:decode(bytes(q),atlas))
    tests['truncation']=rejected(lambda:decode(p[:-1],atlas))
    q=bytearray(p);q[2008:2040]=bytes(32)
    changed=decode(bytes(q),atlas);golden=(build/'expected-1.idx').read_bytes()
    bad=[i for i,(a,b) in enumerate(zip(changed,golden)) if a!=b]
    tests['obj_payload_pixel_detection']=bool(bad) and all(40<=i%256<=47 and 80<=i//256<=87 for i in bad)
    assert all(tests.values()),tests
    normal=[cases[k] for k in ('top','bottom','fine_x')]
    return dict(candidate='NES-R2-SPRITE-REPLAY-023',audit_pass=True,cases=cases,source_sprite_evidence=source,
         full240_sprite_coverage=coverage,unique_sprite_source_pixels=245760,
         normal_actual_pixel_comparisons=3*4*256*239,software_negative_tests=tests,
         packet_bytes=2052,packet_stride_bytes=4096,ppu_dma_bytes=2032,startup_dma_bytes=16384+544,
         max_normal_consumer_clocks=max(c['max_commit_master_clocks'] for c in normal),
         min_normal_margin_clocks=min(c['min_commit_margin_master_clocks'] for c in normal),
         delta_from022=dict(packet_bytes=44,ppu_dma_bytes=44,max_normal_consumer_clocks=21470-19618),
         source_height=240,simultaneous_display_height=239,live_producer_deadline_proven=False,
         combined_fine_x_and_visible_sprite_reference=False,
         verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         scope='One front8x8sprite from actual NES OAM/CHR reads,actual nativeSNES OBJ replay;separate fine-X1/no-sprite regression. No general sprite priority/evaluation/overflow/8x16 or live producer/hardware claim.')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('runs','workloads','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();result=verify(a.runs,a.workloads)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','source_sprite_evidence','full240_sprite_coverage')},indent=2))