# SPDX-License-Identifier: MIT
"""Same-frame linear-span wire/CPU feasibility, with unchanged receipt contract.

Independent Python reconstruction only. No new receiver or DMA-time claim.
"""
from pathlib import Path
import argparse,csv,json,struct,shutil
from nes_delta231 import BASE,sha
from analyze_nes_mapjoint247 import bitmap,encode as maskencode
from analyze_nes_batchorder247 import join
from analyze_nes_geometry230 import packets


def spans(words,gap,cap):
    runs=[]
    for w in sorted(words):
        at=w*2
        if runs and at-runs[-1][1]<=gap:runs[-1]=(runs[-1][0],at+2)
        else:runs.append((at,at+2))
    return [(at,min(cap,end-at)) for start,end in runs for at in range(start,end,cap)]


def encode(ranges,data,packed):
    out=[];records=[]
    for at,n in ranges:
        assert at%2==n%2==0 and 0<n<=236 and at+n<=4096
        records.append(struct.pack('<HB',at,n//2)+data[at:at+n])
    if packed:
        b=bytearray([3])
        for rec in records:
            if len(b)+len(rec)>240:out.append((0,bytes(b)));b=bytearray([3])
            b+=rec
        if len(b)>1:out.append((0,bytes(b)))
    else:out=[(at,data[at:at+n]) for at,n in ranges]
    return out


def decode(wire,packed,base,initialized,manifest):
    result=bytearray(base);end=0;received=set()
    for address,payload in wire:
        if not payload or len(payload)>240:raise ValueError('packet length')
        at=0
        if packed:
            if address or payload[0]!=3 or len(payload)<6:raise ValueError('mode/header')
            at=1
        while at<len(payload):
            if packed:
                if at+3>len(payload):raise ValueError('partial header')
                offset,n=struct.unpack_from('<HB',payload,at);n*=2;at+=3
            else:offset,n=address,len(payload)
            if offset%2 or n%2 or not 0<n<=236 or offset<end or offset+n>4096 or at+n>len(payload):raise ValueError('span bounds/order')
            result[offset:offset+n]=payload[at:at+n];received.update(range(offset//2,(offset+n)//2));at+=n;end=offset+n
    actual=bitmap(received)
    if len(manifest)!=2 or manifest!=[(0,actual[:240]),(240,actual[240:])]:raise ValueError('manifest')
    if not initialized and len(received)!=2048:raise ValueError('cold coverage')
    return bytes(result),received


def guards():
    data=bytes((i*19+7)&255 for i in range(4096));base=bytes(4096);ranges=[(0,2),(14,6),(4094,2)];count=0
    for packed in (False,True):
        wire=encode(ranges,data,packed);receipt={i//2 for at,n in ranges for i in range(at,at+n,2)};m=bitmap(receipt);manifest=[(0,m[:240]),(240,m[240:])]
        got,received=decode(wire,packed,base,True,manifest);assert received==receipt
        want=bytearray(base)
        for at,n in ranges:want[at:at+n]=data[at:at+n]
        assert got==want
        bad=[(wire+wire,True,manifest),(wire[:-1],True,manifest),(wire,False,manifest),(wire,True,manifest[::-1]),(wire,True,manifest[:1]),(wire,True,[(0,bytes(240)),manifest[1]])]
        if packed:
            for offset,n,extra in [(1,1,bytes(2)),(4096,1,bytes(2)),(4094,2,bytes(4)),(0,0,b''),(0,119,bytes(238)),(0,2,bytes(2))]:bad.append(([(0,b'\x03'+struct.pack('<HB',offset,n)+extra)],True,manifest))
            bad.append(([(0,b'\x04'+wire[0][1][1:])],True,manifest))
        else:
            for offset,payload in [(1,bytes(2)),(4096,bytes(2)),(4094,bytes(4)),(0,b''),(0,bytes(238)),(0,bytes(3))]:bad.append(([(offset,payload)],True,manifest))
        for w,init,mf in bad:
            try:decode(w,packed,base,init,mf)
            except ValueError:count+=1
            else:raise AssertionError('bad span accepted')
    # Matching manifests must not hide an odd literal length/alignment error.
    for offset,payload,receipt in [(0,bytes(3),{0}),(1,bytes(2),{0})]:
        m=bitmap(receipt)
        try:decode([(offset,payload)],False,base,True,[(0,m[:240]),(240,m[240:])])
        except ValueError as e:assert str(e)=='span bounds/order';count+=1
        else:raise AssertionError('unaligned literal accepted')
    return count


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('test','timing','model','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);pins={}
 def pin(f):pins[f.resolve().relative_to(BASE).as_posix()]=sha(f);return f
 def read(f):return json.loads(pin(f).read_text(encoding='utf-8'))
 for n in ('nes_delta231.py','analyze_nes_mapjoint247.py','analyze_nes_batchorder247.py','analyze_nes_geometry230.py'):pin(Path(__file__).parent/n)
 timing=read(a.timing/'result.json');model=read(a.model/'result.json');test=read(a.test/'result.json');assert all(r['passed'] for r in (timing,model,test))
 bygen={g:[] for g in range(1,72)}
 for f in sorted((a.test/'run').glob('req-*.bin')):
  b=pin(f).read_bytes();bygen[int.from_bytes(b[8:10],'little')].append(b)
 modes={'literal_exact64':(0,64,False),'packed_exact64':(0,64,True),'packed_gap16_64':(16,64,True),'packed_gap96_64':(96,64,True),'packed_gap96_236':(96,236,True)}
 banks={k:[bytes(4096),bytes(4096)] for k in modes};initialized={k:[False,False] for k in modes};last=bytes(4096);stale=[set(range(2048)),set(range(2048))];rows=[];totalbytes=0
 for g in range(1,72):
  current=pin(a.test/f'run/expected-{g}.bin').read_bytes()[:4096];bank=(g-1)%2;frame=g+904;before=timing['rows'][g-1];m=model['rows'][g-1];assert before['frame']==m['frame']==frame
  changed={w for w in range(2048) if current[w*2:w*2+2]!=last[w*2:w*2+2]}
  for st in stale:st.update(changed)
  words=stale[bank];oldwire,_=maskencode('mask8',words,current);pp=bygen[g]
  assert oldwire==[b[16:] for b in pp if b[0]==9]
  # Reuse the prior model's ready phase, not an inferred runtime ready trace.
  original_paths=[n for n in model['input_hashes'] if n.endswith(f'frame{frame}.packets')];assert len(original_paths)==1
  original=list(packets(pin(BASE/original_paths[0]).read_bytes()));data_count=len(original)-2
  old_count=data_count-sum(b[1]==2 and b[0] not in (1,3) for b in original)+len(oldwire)+2
  # Bulk pattern packets already carry separate control/ready charges in P0.
  # They must not also enter the ordinary DATA ready grouping.
  bulk_count=sum(b[0]==7 for b in pp);nonbulk_count=len(pp)-2-bulk_count
  assert old_count==nonbulk_count,(frame,old_count,nonbulk_count)
  oldmap=sum(len(b)+19 for b in oldwire);base4=m['models']['mask8']['ready4'];base1=m['models']['mask8']['ready1'];assert base4==before['wire_ready4']
  basecharge=m['models']['mask8']['charge'];oldcommands=join([(2,w*2,2) for w in sorted(words)]);fixed_ms=sum(before[k+'_ms'] for k in ('mark','manifest','coverage'))
  for name,(gap,cap,packed) in modes.items():
   rr=spans(words,gap,cap);wire=encode(rr,current,packed);covered={w for at,n in rr for w in range(at//2,(at+n)//2)};bm=bitmap(covered)
   got,received=decode(wire,packed,banks[name][bank],initialized[name][bank],[(0,bm[:240]),(240,bm[240:])]);assert got==current and received==covered and words<=covered
   banks[name][bank]=got;initialized[name][bank]=True;totalbytes+=4096
   commands=join([(2,at,n) for at,n in rr]);assert commands==oldcommands,(name,frame)
   newmap=sum(len(b)+19 for at,b in wire);new_count=old_count-len(oldwire)+len(wire)
   ready4=base4+newmap-oldmap+20*((new_count+3)//4-(old_count+3)//4);ready1=base1+newmap-oldmap+20*(new_count-old_count)
   budget4=1000/60-ready4*8/2625-fixed_ms;budget1=1000/60-ready1*8/2625-fixed_ms
   row=dict(frame=frame,mode=name,required_words=len(words),sent_words=len(covered),extra_words=len(covered-words),records=len(rr),packets=len(wire),mask_packets=len(oldwire),map_wire=newmap,mask_map_wire=oldmap,ready4=ready4,ready1=ready1,wire_delta4=ready4-base4,charge=basecharge,dma_commands_equal=True,old_modeled_data_count=old_count,actual_nonbulk_data_packets=nonbulk_count,actual_bulk_packets=bulk_count,fixed_measured_ms=fixed_ms,mark_ms=before['mark_ms'],manifest_ms=before['manifest_ms'],coverage_ms=before['coverage_ms'],mask_baseline_decoder_budget4_ms=1000/60-base4*8/2625-fixed_ms,new_decoder_budget4_ms=budget4,new_decoder_budget1_ms=budget1,break_even_vs_mask_ms=before['mask_ms']-(ready4-base4)*8/2625,new_decoder_clocks=None,new_body_bytes=None)
   rows.append(row)
  last=current;stale[bank].clear()
 stats=lambda x:dict(minimum=min(x),maximum=max(x),total=sum(x));summary={}
 for name in modes:
  warm=[r for r in rows if r['mode']==name and r['frame']>=907]
  summary[name]={k:stats([r[k] for r in warm]) for k in ('sent_words','extra_words','records','packets','ready4','ready1','wire_delta4','new_decoder_budget4_ms','new_decoder_budget1_ms','break_even_vs_mask_ms')}
  summary[name].update(negative_decoder_budget4=[r['frame'] for r in warm if r['new_decoder_budget4_ms']<=0],negative_decoder_budget1=[r['frame'] for r in warm if r['new_decoder_budget1_ms']<=0],cannot_beat_mask_even_free=[r['frame'] for r in warm if r['break_even_vs_mask_ms']<=0])
 result=dict(passed=True,scope=__doc__,frames=71,modes=modes,exact_map_bytes=totalbytes,normal_reconstructions=len(rows),python_negative_cases=guards(),same_final_map_dma_all=True,manifest_bytes=256,manifest_packets=2,changed_manifest_is_actual_write_superset=True,summary=summary,rows=rows,input_hashes=pins,script_sha256=sha(Path(__file__)),implementation_selected=None,physical=False,full_arm=False,fit=False,
 limitations=['Python reconstruction and wire-ready scenarios only;no new actual decoder or DMA cycles.','Budget holds measured non-map mark/manifest/coverage fixed and replaces mask time;other dispatch/copy/source/ARM/gaps/finalDMA/display remain excluded.','Negative budget disproves only this conditional serial schedule,not every overlapping design.','Span covers extra current-map words;manifest must match actual received superset,not original stale bits.','Gap at most96 and exact span endpoints preserve final map DMA list;remaining952/955 VBlank costs persist.'])
 raw=a.out/'result.json';raw.write_text(json.dumps(result,indent=2)+'\n');public={k:v for k,v in result.items() if k not in ('rows','input_hashes')};public.update(input_count=len(pins),private_result_sha256=sha(raw));(a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n')
 with (a.out/'frames.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
 shutil.copyfile(__file__,a.out/'analyzer.py');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
