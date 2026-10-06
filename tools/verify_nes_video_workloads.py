# Audit actual Mapper4 feature workloads and packet limits. SPDX-License-Identifier: MIT.
from pathlib import Path
from collections import Counter
import argparse,hashlib,json
from verify_nes_rtl_fetch import pixel_coordinate,RGB,oracle
from build_nes_trace_replay import packet,convert,decode
from nes_video_packet_admission import admit
from analyze_nes_fetch_workload import describe
CASES=('baseline','fine_x','sprite','split','banks32')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_case(root,case):
    build=root/case/'build';capture=root/case/'capture'
    m=json.loads((build/'manifest.json').read_text());c=json.loads((capture/'capture.json').read_text())
    assert m['case']==c['case']==case and c['exit_code']==0
    assert sha(build/'mmc3.nes')==m['sha256']==c['rom_sha256']
    rom=(build/'mmc3.nes').read_bytes();chrdata=rom[16+65536:]
    assert len(chrdata)==m['chr_bytes'] and rom[5]*8192==len(chrdata)
    assert bytes(int(v,16) for v in (build/'chr.hex').read_text().split())==chrdata
    raw=[]
    for s in (capture/'trace.tsv').read_text().splitlines():
        kind,*v=s.split();raw.append((kind,*map(int,v)))
    inverse={v:k for k,v in RGB.items()}
    result=[];by_frame={};allbg=[];allchr=[]
    slots=Counter((line,dot) for line in range(-1,240) for k in range(34)
                  for dot in ((8*k+5,8*k+7) if k<32 else (325+8*(k-32),327+8*(k-32))))
    for row in (capture/'frames.tsv').read_text().splitlines():
        f,w,h,mask,ctrl,sx,sy,group,counter,irqs=map(int,row.split())
        assert (w,h)==(256,240) and counter==irqs
        rgb=(capture/f'frame-{f:03}.rgb').read_bytes();assert len(rgb)==256*240*3
        indexed=bytes(inverse[rgb[i:i+3]] for i in range(0,len(rgb),3))
        by_frame[f]=indexed;reads=[];seq=[];writes=[]
        for kind,frame,line,dot,tick,cpu,addr,value,physical in raw:
            if frame!=f:continue
            if kind=='read':
                assert 0<=physical<len(chrdata) and chrdata[physical]==value
                event=dict(frame=f,line=line,dot=dot,tick=tick,offset=physical,tile=physical//16,value=value,pixel=None)
                reads.append(event)
                if (line,dot) in slots:
                    pos=pixel_coordinate(line,dot)
                    event=dict(event,pixel=None if pos is None else list(pos));seq.append(event)
            elif kind=='ppu_write' and -1<=line<240:writes.append([line,dot,addr,value])
        assert Counter((e['line'],e['dot']) for e in seq)==slots
        assert sum(e['pixel'] is not None for e in seq)==15360
        assert all(b['tick']>a['tick'] for a,b in zip(seq,seq[1:]))
        features=dict(ppu_mask=mask,ppu_ctrl=ctrl,scroll_x=sx,scroll_y=sy,
                      active_ppu_writes=writes,immutable_chr_rom=True)
        decision,p=admit(f,seq,chrdata,features,indexed)
        primitive=dict(encoded=False,decoded=False,different_pixels=None)
        try:
            unchecked,_=packet(f,seq);primitive['encoded']=True
            restored=decode(unchecked,convert(chrdata));primitive['decoded']=True
            primitive['different_pixels']=sum(a!=b for a,b in zip(restored,indexed))
        except (AssertionError,ValueError) as exc:primitive['error']=str(exc)
        base=oracle(chrdata,group*1024)
        mismatch=[i for i,(a,b) in enumerate(zip(base,indexed)) if a!=b]
        mapper_visible=[(line,dot,addr,value) for kind,frame,line,dot,tick,cpu,addr,value,physical in raw
                        if frame==f and kind=='mapper_write' and 0<=line<240 and addr in (0x8000,0x8001)]
        result.append(dict(frame=f,rom_counter=counter,group=group,features=features,
            all_chr_reads=len(reads),bg_pattern_reads=len(seq),unique_bg_tiles=len({e['tile'] for e in seq}),
            decision=decision,unchecked_primitive=primitive,different_from_unmodified_bg=len(mismatch),
            difference_bounds=None if not mismatch else dict(min_x=min(i%256 for i in mismatch),max_x=max(i%256 for i in mismatch),
                min_y=min(i//256 for i in mismatch),max_y=max(i//256 for i in mismatch)),
            visible_mapper_writes=mapper_visible,indexed_sha256=hashlib.sha256(indexed).hexdigest()))
        allbg+=seq;allchr+=reads
        if case=='baseline':
            assert decision['accepted'] and not mismatch
        elif case=='fine_x':
            assert sx==1 and not decision['accepted'] and primitive['decoded'] and primitive['different_pixels']>0
        elif case=='sprite':
            assert mask&16 and not decision['accepted'] and primitive['decoded'] and primitive['different_pixels']>0
            assert mismatch and all(40<=i%256<48 and 80<=i//256<88 for i in mismatch)
        elif case=='split':
            assert not decision['accepted'] and not primitive['encoded'] and mapper_visible and mismatch
        else:
            assert len(chrdata)==32768 and not decision['accepted'] and not mismatch
    assert [r['frame'] for r in result]==[6,7,8,9]
    assert len({r['group'] for r in result})==(4 if case=='banks32' else 2)
    if case=='baseline':
        first=[e for e in allbg if e['frame']==6]
        feature=result[0]['features'];ref=by_frame[6]
        negative={}
        for name,badfeature in [('missing',{}),('sprite',dict(feature,ppu_mask=30)),
            ('scroll',dict(feature,scroll_x=1)),('mutable_chr',dict(feature,immutable_chr_rom=False)),
            ('active_write',dict(feature,active_ppu_writes=[[50,20,8197,1]]))]:
            negative[name]=not admit(6,first,chrdata,badfeature,ref)[0]['accepted']
        bad=bytearray(ref);bad[0]^=1
        negative['reference_corruption']=not admit(6,first,chrdata,feature,bytes(bad))[0]['accepted']
        negative['missing_fetch']=not admit(6,first[:-1],chrdata,feature,ref)[0]['accepted']
        # Remove a pixel-used plane, not an unused terminal fetch.
        trim=first.copy();trim.pop(next(i for i,e in enumerate(trim) if e['pixel'] is not None))
        negative['missing_pixel_plane']=not admit(6,trim,chrdata,feature,ref)[0]['accepted']
        for field,value in [('value',first[0]['value']^1),('tile',first[0]['tile']^1),
                            ('tick',first[1]['tick']),('frame',99)]:
            changed=[dict(e) for e in first];changed[0][field]=value
            negative['event_'+field]=not admit(6,changed,chrdata,feature,ref)[0]['accepted']
        return result,allbg,allchr,negative,chrdata
    return result,allbg,allchr,{},chrdata
def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert not a.out.exists()
    cases={};neg={}
    for case in CASES:
        frames,bg,allchr,tests,chrdata=read_case(a.runs,case)
        neg.update(tests)
        policies=[describe(bg,cap)[0] for cap in (256,512,1024,2048)]
        cases[case]=dict(frames=frames,chr_rom_bytes=len(chrdata),observed_bg_union_tiles=len({e['tile'] for e in bg}),
                         all_chr_reads=len(allchr),bg_reads=len(bg),policies=policies)
    assert all(neg.values())
    result=dict(candidate='NES-R2-VIDEO-WORKLOADS-021',audit_pass=True,cases=cases,admission_negative_tests=neg,
                actual_emulator_frames=20,source_pixels=20*256*240,
                accepted_frames=4,rejected_unsupported_frames=16,
                new_rtl_execution=False,new_snes_execution=False,
                scope='New original NES Mesen workload/reference captures and conservative offline packet admission; no new RTL equivalence or live hardware transport.',
                verifier_sha256=sha(__file__))
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(audit_pass=True,admission_negative_tests=neg,cases={k:[
      dict(frame=f['frame'],decision=f['decision'],unchecked=f['unchecked_primitive'],bounds=f['difference_bounds'])
      for f in v['frames']] for k,v in cases.items()}),indent=2))
if __name__=='__main__':main()