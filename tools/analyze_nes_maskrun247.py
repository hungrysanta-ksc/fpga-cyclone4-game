# SPDX-License-Identifier: MIT
"""Independent map/command oracle and actual expanded-consumer timing ledger."""
from pathlib import Path
import argparse,csv,json,re
from nes_delta231 import BASE,sha
from analyze_nes_mapjoint247 import encode,bitmap,decode
from analyze_nes_batchorder247 import join

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('test','host','client','fault','storage','rtl','model','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);pins={}
 def pin(f):pins[f.resolve().relative_to(BASE).as_posix()]=sha(f);return f
 def read(f):return json.loads(pin(f).read_text(encoding='utf-8'))
 test=read(a.test/'result.json');host=read(a.host/'result.json');fault=read(a.fault/'result.json');storage=read(a.storage/'result.json');rtl=read(a.rtl/'result.json')
 assert all(r['passed'] for r in (test,host,fault,storage,rtl)) and test['commits']==71 and len(fault['cases'])==12
 for n,h in test['inputs'].items():assert sha(pin(BASE/n))==h
 for n,h in host['output_hashes'].items():assert sha(pin(a.host/n))==h
 run=a.test/'run';model=list(csv.DictReader(pin(a.model).open()));assert len(model)==71
 packets={g:[] for g in range(1,72)}
 for f in sorted(run.glob('req-*.bin')):
  b=pin(f).read_bytes();g=int.from_bytes(b[8:10],'little');packets[g].append((f,b))
 phase={};pending={};shared_returns=0
 for x in csv.DictReader(pin(run/'mask-phase247.csv').open()):
  g=int(x['generation']);name=x['event'];t=int(x['master_clock']);k=name.replace('_return247','').replace('212','').replace('247','')
  if '_return' not in name:assert (g,k) not in pending;pending[g,k]=t
  elif (g,k) in pending:phase.setdefault(g,{}).setdefault(k,[]).append(t-pending.pop((g,k)))
  else:assert name=='manifest_return247';shared_returns+=1
 assert not pending
 last=bytes(4096);banks=[bytes(4096),bytes(4096)];valid=[set(),set()];stale=[set(range(2048)),set(range(2048))];rows=[];allowed=set();totcommands=totbytes=mapchecks=0
 for g in range(1,72):
  m=model[g-1];frame=g+904;bank=(g-1)%2;assert int(m['frame'])==frame
  want=pin(run/f'expected-{g}.bin').read_bytes()[:4096]
  changed={w for w in range(2048) if want[2*w:2*w+2]!=last[2*w:2*w+2]}
  for st in stale:st.update(changed)
  wire,recs=encode('mask8',stale[bank],want);expectedbitmap=bitmap(stale[bank])
  actualwire=[b[16:] for _,b in packets[g] if b[0]==9];assert wire==actualwire
  manifest=[(int.from_bytes(b[10:12],'little'),b[16:]) for _,b in packets[g] if b[0]==10]
  assert manifest==[(0,expectedbitmap[:240]),(240,expectedbitmap[240:])]
  got,valid[bank],received=decode('mask8',wire,banks[bank],valid[bank],manifest);assert got==want
  assert len(received)==int(m['causal_target_words']);mapchecks+=4096;banks[bank]=want;last=want;stale[bank].clear()
  ranges=[];pattern={0:set(),1:set()}
  for f,b in packets[g]:
   op,kind=b[:2];at=int.from_bytes(b[10:12],'little');n=int.from_bytes(b[14:16] if op in (4,5,7,8) else b[12:14],'little')
   if op==7:
    assert len(pin(f.with_name(f.name.replace('req-','tile-'))).read_bytes())==n
    ranges.append((kind,at,n));pattern[kind].update(range(at,at+n))
   elif op==9:
    i=17
    while i<len(b):
     group,mask=b[i:i+2];i+=2
     for bit in range(8):
      if mask>>bit&1:ranges.append((2,group*16+bit*2,2));i+=2
    assert i==len(b)
   elif kind==5 and op in (2,4,5) and at>=1121 and at<3169:ranges.append((5,at-1121,min(n,3169-at)))
  expected=[]
  for k,at,n in join(ranges):
   src,da,db={0:(0,0,0xc000),1:(0x4000,0x4000,0x8000),2:(0x5000,0x6000,0xa000),5:(0x6961,0x5000,0x9000)}[k]
   expected.append(dict(source=bank*0x8000+src+at,destination=(db if bank else da)+at,bytes=n))
   if k<2:allowed.update(0x7f0000+bank*0x8000+src+i for i in range(at,at+n) if i not in pattern[k])
  actual=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(pin(run/f'commands-{g}.csv').open())];assert actual==expected,(frame,actual,expected)
  totcommands+=len(actual);totbytes+=sum(x['bytes'] for x in actual)
  pp=phase[g];assert len(pp['mask'])==len(wire) and len(pp['manifest'])==2 and len(pp['coverage'])==1
  assert len(pp['mark'])==sum(b[0] in (2,4,5,7,8) for _,b in packets[g])
  row=dict(frame=frame,map_words=len(received),map_records=len(recs),map_packets=len(wire),manifest_packets=2,commands=len(actual),dma_bytes=sum(x['bytes'] for x in actual),vblanks=int(pin(run/f'vblank-{g}.txt').read_text()))
  for k in ('mark','mask','manifest','coverage'):row[k+'_clocks']=sum(pp[k]);row[k+'_ms']=sum(pp[k])/21477.270
  row['wire_ready4']=int(m['mask8.ready4']);row['charge']=int(m['mask8.charge'])
  row['conditional_wire_plus_measured_ms']=row['wire_ready4']*8/2625+sum(row[k+'_ms'] for k in ('mark','mask','manifest','coverage'))
  row['map_and_validation_ms']=sum(row[k+'_ms'] for k in ('mask','manifest','coverage'))
  rows.append(row)
 assert totcommands==test['vram_commands'] and totbytes==test['vram_bytes']
 warnings=[int(x,16) for x in re.findall(r'Uninitialized memory read: \$([0-9A-Fa-f]+)',pin(run/'mesen.log').read_text(errors='replace'))];assert set(warnings)<=allowed
 assert 'reference_checks=4066624' in pin(run/'host.log').read_text()
 stats=lambda k:dict(minimum=min(r[k] for r in rows[2:]),maximum=max(r[k] for r in rows[2:]),total=sum(r[k] for r in rows[2:]))
 resource={}
 for n,v in storage['variants'].items():
  nums={key:int(re.search(label+r'\s*:\s*([\d,]+)',v['summary'])[1].replace(',','')) for key,label in [('le','Total logic elements'),('comb','Total combinational functions'),('ff','Dedicated logic registers'),('memory_bits','Total memory bits')]}
  resource[n]=dict(**nums,rom_rows=v['rom_rows'],warning_count=len(v['warnings']))
 result=dict(passed=True,scope=__doc__,actual_frames=71,exact_map_bytes=mapchecks,exact_command_frames=71,reference_checks=4066624,commands=totcommands,dma_bytes=totbytes,acks=test['acks'],fault_cases=fault['cases'],storage=resource,storage_rtl_reads=rtl['read_checks'],storage_raw_guards=rtl['raw_guards'],split_body_free=storage['split_body_free'],body_bytes=storage['body_bytes'],warm={k:stats(k) for k in rows[0] if k!='frame'},warm_multi_vblank=[r['frame'] for r in rows[2:] if r['vblanks']>1],conditional_serial_over=[r['frame'] for r in rows[2:] if r['conditional_wire_plus_measured_ms']>1000/60],uninitialized_addresses=len(set(warnings)),warnings_only_pattern_gaps=True,shared_manifest_return_ignored=shared_returns,rows=rows,input_hashes=pins,script_sha256=sha(Path(__file__)),selected_implementation=None,physical=False,full_arm=False,fit=False,sta=False,product_changed=False,
 limitations=['Actual65816/Mesen held-mailbox replay,not complete FPGA/ARM or physical FPS.','PC sender retains independent4096B previous map and512B stale bits;not ARM allocation approval.','Mask and manifest timings include their actual decode/staging/append routines;other packet dispatch/copy,source/ARM/gaps/DMA/display are not all counted.','Wire+CPU sum is a conditional serialized schedule,not proof that every overlapping schedule fails.','5KiB RAM geometry inferred at MAP;whole-board placement and M9K/mapper margin remain unverified.'])
 raw=a.out/'result.json';raw.write_text(json.dumps(result,indent=2)+'\n')
 public={k:v for k,v in result.items() if k not in ('rows','input_hashes')};public.update(input_count=len(pins),private_result_sha256=sha(raw))
 (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n')
 with (a.out/'frames.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
 shutil=__import__('shutil');shutil.copyfile(__file__,a.out/'analyzer.py');print(json.dumps({k:public[k] for k in ('actual_frames','commands','dma_bytes','warm_multi_vblank','storage')},indent=2))

if __name__=='__main__':main()
