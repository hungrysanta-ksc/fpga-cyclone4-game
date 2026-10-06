# Raw SNES immutable CHR residency audit and storage bounds. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,hashlib,json
from run_nes_chr_residency import audit
from build_nes_chr_residency import decode,encode,fine_coord
from build_nes_trace_replay import display_rgb
from verify_nes_video_workloads import read_case
def rejected(fn):
    try:fn()
    except (AssertionError,ValueError):return True
    return False
def verify(root,workloads):
    cases={}
    for case in ('top','bottom','fine_x','bank','window'):
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
    for name,offset,value in [('magic',0,0),('version',4,2),('frame',5,0),('fine_range',6,8),('window',7,2),
                             ('width',9,0),('height',10,239),('map_length',16,0),
                             ('tile_range',21,255),('palette',2007,255)]:
        changed=bytearray(p);assert changed[offset]!=value;changed[offset]=value
        negatives[name]=rejected(lambda:decode(bytes(changed),atlas))
    negatives['truncated_packet']=rejected(lambda:decode(p[:-1],atlas))
    negatives['extra_byte']=rejected(lambda:decode(p+b'0',atlas))
    negatives['short_atlas']=rejected(lambda:decode(p,atlas[:16384]))
    changed=bytearray(p);changed[7]^=1
    negatives['valid_wrong_window_pixels']=decode(bytes(changed),atlas)!=(build/'expected-1.idx').read_bytes()
    frames,bg,_,_,chrdata=read_case(workloads,'banks32')
    from build_nes_trace_replay import convert
    assert atlas==convert(chrdata) and len(atlas)==32768
    frame_evidence=[];seen=set()
    for i,info in enumerate(frames,1):
        seq=[e for e in bg if e['frame']==info['frame']]
        encoded=encode(i,seq,info['features'],chrdata)
        assert encoded==(build/f'packet-{i}.bin').read_bytes()
        assert decode(encoded,atlas)==(build/f'expected-{i}.idx').read_bytes()
        tiles={e['tile'] for e in seq if fine_coord(e['line'],e['dot']) is not None}
        fresh=tiles-seen;seen|=tiles
        assert len(tiles)==len(fresh)==256
        frame_evidence.append(dict(frame=i,source_frame=info['frame'],window=encoded[7],
                             physical_tile_min=min(tiles),physical_tile_max=max(tiles),
                             unique_tiles=len(tiles),cold_miss_bytes=16*len(fresh)))
    assert [e['window'] for e in frame_evidence]==[1,0,0,1]
    feature=frames[0]['features'];seq=[e for e in bg if e['frame']==frames[0]['frame']]
    idx=next(i for i,e in enumerate(seq) if fine_coord(e['line'],e['dot']) is not None)
    negatives['missing_plane']=rejected(lambda:encode(1,seq[:idx]+seq[idx+1:],feature,chrdata))
    negatives['duplicate_plane']=rejected(lambda:encode(1,seq+[seq[idx]],feature,chrdata))
    mixed=[]
    for e in seq:
        e=dict(e);pos=fine_coord(e['line'],e['dot'])
        if pos is not None and (pos[0]//8,pos[1])==(0,0):
            off=e['offset']^16384;e.update(offset=off,tile=off//16,value=chrdata[off])
        mixed.append(e)
    negatives['mixed_windows']=rejected(lambda:encode(1,mixed,feature,chrdata))
    negatives['oversized_chr']=rejected(lambda:encode(1,seq,feature,chrdata*2))
    for name,key,value in [('sprite','ppu_mask',30),('vertical','scroll_y',1),('coarse','scroll_x',8),
                           ('mutable','immutable_chr_rom',False),('midframe_ppu','active_ppu_writes',True)]:
        negatives[name]=rejected(lambda:encode(1,seq,dict(feature,**{key:value}),chrdata))
    # Actual captured packet lengths, not ROM slot sizes, set the storage lower bounds.
    repo=Path(__file__).resolve().parents[1]
    samples=[('fine_x022','local-fine-scroll-022'),('sprite023','local-sprite-replay-023'),
             ('split024','local-bank-patch-024'),('residency025','local-chr-residency-025')]
    storage=[]
    for name,folder in samples:
        directory=repo/'analysis'/folder/'top/build'
        lengths=[len((directory/f'packet-{i}.bin').read_bytes()) for i in range(1,5)]
        m=json.loads((directory/'manifest.json').read_text());size=max(lengths)
        assert size==m['packet_bytes']
        blocks=(size+1023)//1024
        power2=1<<(size-1).bit_length()
        storage.append(dict(sample=name,max_packet_bytes=size,excess_over_2KiB=max(0,size-2048),
            slots2_packed_bytes=2*size,slots2_1KiB_rounded_bytes=2*blocks*1024,
            slots2_power2_bytes=2*power2,rom_stride=m['packet_stride'],
            m9k_1024x8_per_slot_arithmetic=blocks,metadata_and_cdc_included=False))
    vram=dict(total_bytes=65536,map_sets_bytes=8192,resident_chr_bytes=32768,
              occupied_bytes=40960,unallocated_bytes=24576,chr_word_start=8192,chr_word_end_exclusive=24576,
              overlaps_023_obj_word16384=True,combined_obj_relocation_tested=False)
    cold=dict(chr_new_bytes_per_sample_frame=4096,map_palette_bytes=1988,total_dma_bytes=6084,
              dma_payload_master_clocks_lower_bound=6084*8,raw_239line_blank_master_clocks=22*1364,
              exceeds_even_raw_blank=6084*8>22*1364,
              scope='Lower bound for on-demand full new4096B plus map/palette in one VBlank;not an executed failing SNES run or all rendering strategies.')
    assert all(negatives.values())
    normal=[cases[name] for name in ('top','bottom','fine_x')]
    return dict(candidate='NES-R2-CHR-RESIDENCY-025',audit_pass=True,cases=cases,full240_banks32_coverage=coverage,
                banks32_unique_source_pixels=245760,normal_actual_pixel_comparisons=3*4*256*239,
                software_negative_tests=negatives,packet_bytes=2008,ppu_dma_bytes=1988,
                delta_from022=dict(packet_bytes=0,ppu_dma_bytes=0,max_normal_consumer_clocks=19732-19618),
                frame_evidence=frame_evidence,packet_storage_bounds=storage,vram=vram,cold_stream_lower_bound=cold,
                max_normal_consumer_clocks=max(c['max_commit_master_clocks'] for c in normal),
                min_normal_deadline_margin=min(c['min_commit_margin_master_clocks'] for c in normal),
                source_height=240,simultaneous_display_height=239,full240_simultaneous_display_proven=False,
                observed_nes_fine_x=[0,1],live_producer_deadline_proven=False,
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='Actual SNES banks32 and separatefine-X1;whole32KiB immutable startup,one16KiBwindow/frame. No mixedwindow,sprite combination,liveproducer or hardware proof.')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('runs','workloads','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();result=verify(a.runs,a.workloads)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','full240_banks32_coverage','frame_evidence')},indent=2))