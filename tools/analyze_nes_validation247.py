# SPDX-License-Identifier: MIT
"""Actual non-map range timing and exact manifest wire feasibility together.

RLE manifest is an independent Python policy model, not a new CPU decoder.
"""
import inspect
import analyze_nes_maskrun247 as base
from nes_delta231 import once


def manifest_wire(bitmap):
    records=[];at=0
    while at<256:
        zero=bitmap[at]==0;end=at+1
        while end<256 and end-at<128 and (bitmap[end]==0)==zero:end+=1
        records.append((at,bytes([(128 if zero else 0)+end-at-1])+(b'' if zero else bitmap[at:end])))
        at=end
    packets=[];payload=bytearray([3]);start=0
    for at,rec in records:
        if len(payload)+len(rec)>240:packets.append((start,bytes(payload)));start=at;payload=bytearray([3])
        payload+=rec
    packets.append((start,bytes(payload)))
    return packets


def manifest_decode(packets):
    out=bytearray()
    for offset,payload in packets:
        if offset!=len(out) or not 2<=len(payload)<=240 or payload[0]!=3:raise ValueError('manifest header')
        at=1
        while at<len(payload):
            code=payload[at];at+=1;n=(code&127)+1
            if len(out)+n>256:raise ValueError('manifest overflow')
            if code&128:out+=bytes(n)
            else:
                if at+n>len(payload):raise ValueError('manifest truncated literal')
                out+=payload[at:at+n];at+=n
    if len(out)!=256:raise ValueError('manifest incomplete')
    return bytes(out)


def main():
 s=inspect.getsource(base.main)
 s=once(s,"('test','host','client','fault','storage','rtl','model','out')", "('test','host','client','fault','directed','coverage','baseline','spans','model','out')")
 s=once(s,";storage=read(a.storage/'result.json');rtl=read(a.rtl/'result.json')", ";directed=read(a.directed/'result.json');before=read(a.baseline/'result.json');client=read(a.client/'result.json')")
 s=once(s,'(test,host,fault,storage,rtl)','(test,host,fault,directed,before)')
 a=s.index(' resource={}');b=s.index(' result=dict(',a);s=s[:a]+s[b:]
 a=s.index('storage=resource,');b=s.index('warm={k:stats(k)',a);s=s[:a]+"body_bytes=client['body_bytes'],"+s[b:]
 s=once(s,"'5KiB RAM geometry inferred at MAP;whole-board placement and M9K/mapper margin remain unverified.'", "'No new storage synthesis;5886B requires5984B body capacity of existing6KiB layout,but whole-board area and timing remain unverified.'")
 s=once(s," raw=a.out/'result.json';", ''' assert len(directed['cases'])==6
 coverage=read(a.coverage/'result.json');spans=read(a.spans/'result.json')
 assert coverage['passed'] and len(coverage['cases'])==8 and spans['passed'] and spans['normal_reconstructions']==355
 for folder,item in ((a.fault,fault),(a.directed,directed),(a.coverage,coverage)):
  assert item['client_sha256']==sha(pin(a.client/'sink165.sfc')) and item['normal_sha256']==sha(a.test/'result.json')
  for f in sorted(folder.rglob('*')):
   if f.is_file() and f.suffix in ('.json','.lua','.py','.log'):pin(f)
 checks=list(csv.DictReader(pin(run/'range247.csv').open()));assert checks
 for x in checks:
  start,count,take,bank=(int(x[k]) for k in ('start','count','take','bank'))
  assert count>0 and start+count<=1328 and take==min(16-start%16,count) and bank in (0,166)
 oldrows=before['rows'];assert len(oldrows)==71
 for old,new in zip(oldrows,rows):
  for k in ('frame','map_words','map_records','map_packets','commands','dma_bytes','vblanks','wire_ready4','charge'):assert old[k]==new[k],(k,new['frame'])
  # Exact256B decode includes every omitted zero; no hash or subset check.
  manifests=[(int.from_bytes(b[10:12],'little'),b[16:]) for f,b in packets[new['frame']-904] if b[0]==10]
  mapbits=b''.join(b for at,b in manifests);assert len(mapbits)==256
  compressed=manifest_wire(mapbits);assert manifest_decode(compressed)==mapbits
  rawcost=sum(len(b)+19 for at,b in manifests);rcost=sum(len(b)+19 for at,b in compressed)
  selected=compressed if rcost<rawcost else manifests
  count=len(packets[new['frame']-904])-2-sum(b[0]==7 for f,b in packets[new['frame']-904])
  newcount=count-2+len(selected)
  delta=sum(len(b)+19 for at,b in selected)-rawcost+20*((newcount+3)//4-(count+3)//4)
  new.update(mark_reduction_ms=old['mark_ms']-new['mark_ms'],manifest_model='zero_rle' if selected is compressed else 'existing_dense',manifest_payload=sum(len(b) for at,b in selected),manifest_model_packets=len(selected),manifest_model_wire=sum(len(b)+19 for at,b in selected),manifest_wire_delta4=delta,
   manifest_decoder_allowance_ms=1000/60-(new['wire_ready4']+delta)*8/2625-new['mark_ms']-new['mask_ms']-new['coverage_ms'])
 warm=rows[2:];oldwarm=oldrows[2:]
 compare={}
 for k in ('mark_ms','mask_ms','manifest_ms','coverage_ms','conditional_wire_plus_measured_ms'):
  old=sum(r[k] for r in oldwarm);new=sum(r[k] for r in warm)
  compare[k]=dict(old_total=old,new_total=new,total_reduction_percent=100*(1-new/old),old_max=max(r[k] for r in oldwarm),new_max=max(r[k] for r in warm))
 invalid=[[],[(0,b'\\x03\\xff')],[(1,b'\\x03\\xff\\xff')],[(0,b'\\x04\\xff\\xff')],[(0,b'\\x03\\xff\\xff\\x80')],[(0,b'\\x03\\x01\\x00')],[(0,b'\\x03\\xff'),(0,b'\\x03\\xff')]]
 for bad in invalid:
  try:manifest_decode(bad)
  except ValueError:pass
  else:raise AssertionError('invalid manifest accepted')
 assert manifest_decode(manifest_wire(bytes(256)))==bytes(256)
 assert manifest_decode(manifest_wire(bytes([255])*256))==bytes([255])*256
 joint=[];byframe={r['frame']:r for r in rows}
 # A span superset needs its OWN expanded receipt, never the mask receipt.
 from analyze_nes_spantrade247 import spans as make_spans
 pin(BASE/'repository-nes-milestone/tools/analyze_nes_spantrade247.py')
 for oldspan in spans['rows']:
  frame=oldspan['frame'];r=byframe[frame];g=frame-904
  wire=[b[16:] for f,b in packets[g] if b[0]==9];words=set()
  for payload in wire:
   at=1
   while at<len(payload):
    group,mask=payload[at:at+2];at+=2
    for bit in range(8):
     if mask>>bit&1:words.add(group*8+bit);at+=2
  assert len(words)==oldspan['required_words'] and sum(len(b)+19 for b in wire)==oldspan['mask_map_wire']
  gap,cap,packed=spans['modes'][oldspan['mode']]
  covered={w for start,n in make_spans(words,gap,cap) for w in range(start//2,(start+n)//2)}
  exact=bitmap(covered);encoded=manifest_wire(exact);assert manifest_decode(encoded)==exact
  dense=[(0,exact[:240]),(240,exact[240:])]
  chosen=encoded if sum(len(b)+19 for at,b in encoded)<294 else dense
  mfwire=sum(len(b)+19 for at,b in chosen);oldcount=oldspan['old_modeled_data_count']
  newcount=oldcount-r['map_packets']+oldspan['packets']-2+len(chosen)
  ready4=r['wire_ready4']+oldspan['map_wire']-oldspan['mask_map_wire']+mfwire-294+20*((newcount+3)//4-(oldcount+3)//4)
  allowance=1000/60-ready4*8/2625-r['mark_ms']-r['coverage_ms']
  joint.append(dict(frame=frame,mode=oldspan['mode'],records=oldspan['records'],map_packets=oldspan['packets'],manifest_packets=len(chosen),manifest_payload=sum(len(b) for at,b in chosen),ready4=ready4,map_and_manifest_decoder_allowance_ms=allowance,new_map_decoder_measured=False,new_manifest_decoder_measured=False))
 joint_summary={}
 for mode in spans['modes']:
  rr=[r for r in joint if r['mode']==mode and r['frame']>=907]
  joint_summary[mode]=dict(minimum_decoder_allowance_ms=min(r['map_and_manifest_decoder_allowance_ms'] for r in rr),negative_allowance_frames=[r['frame'] for r in rr if r['map_and_manifest_decoder_allowance_ms']<=0],ready4_max=max(r['ready4'] for r in rr))
 with (a.out/'joint-frames.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=joint[0],lineterminator='\\n');w.writeheader();w.writerows(joint)
 result.update(joint_summary=joint_summary,joint_model_rows=len(joint),comparison=compare,directed_fault_cases=directed['cases'],coverage_fault_cases=coverage['cases'],range_chunks=len(checks),bitmap_bytes_checked_per_chunk=498,range_bitmap_byte_checks=498*len(checks),range_banks=sorted({int(x['bank']) for x in checks}),range_starts_mod16=sorted({int(x['start'])%16 for x in checks}),
  manifest_python_negatives=len(invalid),manifest_reconstructions=71,manifest_new_decoder=False,manifest_model_warm_delta4=sum(r['manifest_wire_delta4'] for r in warm),manifest_model_negative_allowance=[r['frame'] for r in warm if r['manifest_decoder_allowance_ms']<=0],mark_regression_frames=[r['frame'] for r in warm if r['mark_reduction_ms']<0],baseline_sha256=sha(a.baseline/'result.json'))
 result['limitations'].append('RLE manifest holds actual new mark/mask/coverage times;its new decode time is unknown. Negative allowance is conditional serial only. No new protocol selected.')
 raw=a.out/'result.json';''')
 s=once(s,"('actual_frames','commands','dma_bytes','warm_multi_vblank','storage')", "('actual_frames','commands','dma_bytes','warm_multi_vblank','comparison','manifest_model_negative_allowance')")
 ns=dict(base.__dict__);ns.update(manifest_wire=manifest_wire,manifest_decode=manifest_decode,__file__=__file__,__doc__=__doc__)
 exec(compile(s,'validation247-analysis','exec'),ns);ns['main']()


if __name__=='__main__':main()
