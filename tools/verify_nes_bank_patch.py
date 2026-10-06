# Raw SNES bank patch audit and reserved-slot regressions. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,hashlib,json
from run_nes_bank_patch import audit
from nes_bank_patch_packet import decode,encode,BASE,CAPACITY
from build_nes_fine_scroll import fine_coord
from build_nes_trace_replay import display_rgb
from verify_nes_video_workloads import read_case
def rejected(fn):
    try:fn()
    except (AssertionError,ValueError):return True
    return False
def verify(root,workloads):
    cases={}
    for case in ('top','bottom','fine_x','patch','count'):
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
    for name,offset,value in [('magic',0,0),('version',4,2),('frame',5,0),('fine_range',6,8),
                             ('count',7,33),('width',9,0),('height',10,239),('map_length',16,0),
                             ('tile_range',21,255),('palette',2007,255)]:
        changed=bytearray(p);assert changed[offset]!=value;changed[offset]=value
        negatives[name]=rejected(lambda:decode(bytes(changed),atlas))
    negatives['truncated_packet']=rejected(lambda:decode(p[:-1],atlas))
    negatives['extra_packet_byte']=rejected(lambda:decode(p+b'0',atlas))
    changed=bytearray(p);changed[2008:]=bytes(len(p)-2008)
    restored=decode(bytes(changed),atlas);expected=(build/'expected-1.idx').read_bytes()
    bad=[i for i,(a,b) in enumerate(zip(restored,expected)) if a!=b]
    negatives['patch_pixel_detection']=bool(bad) and all(56<=i//256<=63 for i in bad)
    changed=bytearray(p);changed[20:22]=(BASE+CAPACITY-1).to_bytes(2,'little')
    negatives['unwritten_reserved_slot']=rejected(lambda:decode(bytes(changed),atlas))
    frames,bg,_,_,chrdata=read_case(workloads,'split')
    patch_evidence=[]
    for i,info in enumerate(frames,1):
        seq=[e for e in bg if e['frame']==info['frame']]
        encoded,records=encode(i,seq,info['features'],chrdata)
        assert encoded==(build/f'packet-{i}.bin').read_bytes()
        assert len(records)==20 and all(r['cell'][0]==7 for r in records)
        assert decode(encoded,atlas)==(build/f'expected-{i}.idx').read_bytes()
        patch_evidence.append(dict(frame=i,patch_count=len(records),patch_bytes=len(encoded)-2008,records=records))
    feature=frames[0]['features'];seq=[e for e in bg if e['frame']==frames[0]['frame']]
    idx=next(i for i,e in enumerate(seq) if fine_coord(e['line'],e['dot']) is not None)
    negatives['missing_plane']=rejected(lambda:encode(1,seq[:idx]+seq[idx+1:],feature,chrdata))
    negatives['duplicate_plane']=rejected(lambda:encode(1,seq+[seq[idx]],feature,chrdata))
    def changed_sequence(mode):
        output=[]
        for e in seq:
            e=dict(e);pos=fine_coord(e['line'],e['dot'])
            if pos is not None:
                y,x=pos
                if mode=='collision' and (y//8,x)==(0,0):
                    off=BASE*16+e['offset']%16
                elif mode=='capacity' and y==7:
                    off=e['offset']^8192
                else:off=e['offset']
                e.update(offset=off,tile=off//16,value=chrdata[off])
            output.append(e)
        return output
    negatives['active_reserved_collision']=rejected(lambda:encode(1,changed_sequence('collision'),feature,chrdata))
    negatives['capacity_overflow']=rejected(lambda:encode(1,changed_sequence('capacity'),feature,chrdata))
    for name,key,value in [('sprite','ppu_mask',30),('vertical','scroll_y',1),('coarse','scroll_x',8),
                           ('mutable','immutable_chr_rom',False),('midframe_ppu','active_ppu_writes',True)]:
        negatives[name]=rejected(lambda:encode(1,seq,dict(feature,**{key:value}),chrdata))
    assert all(negatives.values())
    normal=[cases[name] for name in ('top','bottom','fine_x')]
    return dict(candidate='NES-R2-BANK-PATCH-024',audit_pass=True,cases=cases,full240_split_coverage=coverage,
                split_unique_source_pixels=245760,normal_actual_pixel_comparisons=3*4*256*239,
                software_negative_tests=negatives,packet_bytes=2328,ppu_dma_bytes=2308,patch_evidence=patch_evidence,
                delta_from022=dict(packet_bytes=320,ppu_dma_bytes=320,
                    max_normal_consumer_clocks=22788-19618),
                max_normal_consumer_clocks=max(c['max_commit_master_clocks'] for c in normal),
                min_normal_deadline_margin=min(c['min_commit_margin_master_clocks'] for c in normal),
                source_height=240,simultaneous_display_height=239,full240_simultaneous_display_proven=False,
                observed_nes_fine_x=[0,1],live_producer_deadline_proven=False,
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='Actual SNES captured in-cell bank split and separate fine-X1 replay;offline packets/full immutable16KiB CHR preload with reserved32patch slots. No sprite combination,largeCHR,live producer or hardware proof.')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('runs','workloads','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();result=verify(a.runs,a.workloads)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','full240_split_coverage')},indent=2))