# SPDX-License-Identifier: MIT
"""Per-record measured CPU service:reference386 or incremental388,375RTL/377M4.

The paired reference separates the allocation correction from implementation.
Native init delta and first-map initialization are charged,not free overlap.
"""
import csv,json,os,shutil,sys
reference='--reference-cpu' in sys.argv
if reference:sys.argv.remove('--reference-cpu');os.environ['NES389_REF_CPU']='1'
reference=reference or os.environ.get('NES389_REF_CPU')=='1'
import probe_nes_burst387 as previous
from nes_delta231 import ROOT,BASE,sha,once

spool=previous.previous
NATIVE=BASE/('probes/nes-burst386/native08'if reference else'probes/nes-increment388/native07')
spool.NATIVE=NATIVE
old_profile=spool.profile
engine=previous.engine;old_prepare=engine.prepare

def profile(d,f):
 r=old_profile(d,f);q=NATIVE/str(f);jobs=json.loads((q/'fixture.json').read_text())
 ev=[list(map(int,x))for x in csv.reader((q/'events.csv').read_text().splitlines())]
 starts={i:next(x[4]for x in ev if x[0]==i and x[1:3]==[0,0x6001])for i in range(1,len(jobs)+2)}
 overhead=[starts[i+1]-starts[i]-len(bytes.fromhex(j['data']))*8 for i,j in enumerate(jobs,1)]
 words=[int(x,16)for x in(d/f'spool-records{f}.hex').read_text().split()]
 assert len(words)==len(overhead)+1 and all(0<=n<1<<24 for n in overhead)
 words=[words[0]]+[x|(n<<40)for x,n in zip(words[1:],overhead)]
 (d/f'spool-records{f}.hex').write_text('\n'.join(f'{x:016x}'for x in words)+'\n')
 ref=BASE/f'probes/nes-burst386/native08/{f}/events.csv'
 oldev=[list(map(int,x))for x in csv.reader(ref.read_text().splitlines())]
 oldfirst=next(x[4]for x in oldev if x[1:3]==[0,0x6001])
 init_delta=max(0,starts[1]-oldfirst)
 cfg=d/f'spool-config{f}.hex';cfg.write_text(cfg.read_text()+f'{init_delta:016x}\n')
 r.update(per_record_control_clocks=overhead,first_source_init_extra_clocks=init_delta,allocation='Per-record observed total service;control before/after native payload is conservatively charged before live reads;not fullCPU lockstep.')
 return r
spool.profile=profile

def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];p=d/'joint266_tb.sv';s=p.read_text()
 for key in ('dut.flow.tkind','2','dut.flow.header[1]'):
  s=once(s,'overhead384['+key+']','records384[record384+1][63:40]')
 s=once(s,'   if(recordlen384||record384>=records384[0])',
  '   if(record384==0)#(config384[8]*MASTER_NS378);\n   if(recordlen384||record384>=records384[0])')
 p.write_text(s,newline='\n');shutil.copyfile(ROOT/'tools/probe_nes_increment389.py',d/'probe_nes_increment389.py')
 nr=json.loads((NATIVE/'result.json').read_text());body=nr['cases'][0]['body_bytes'];ram=nr['WRAM']['total'];dp=30 if reference else 37
 # Inherited generator manifests are provenance,not stale candidate ledgers.
 for filename,fields in [('manifest384.json',dict(WRAM_bytes=ram,finalACK='After actual native PPU service')),
                         ('manifest387.json',dict(ROM_body_bytes=body,payload_record_WRAM_bytes=ram,DP_extra_live_bytes=dp))]:
  q=d/filename;m=json.loads(q.read_text());m.update(fields);q.write_text(json.dumps(m,indent=2)+'\n')
 (d/'manifest389.json').write_text(json.dumps(dict(reference386=reference,native=str(NATIVE),native_result=sha(NATIVE/'result.json'),RTL_changed=False,ARM_changed=False,
  ROM_body_bytes=body,payload_record_WRAM_bytes=ram,additional_DP_reservation_bytes=dp,
  allocation='Per-record source control,including lazyfirst-map init;positive initial CPU delta charged once',scope=__doc__),indent=2)+'\n')
 return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
