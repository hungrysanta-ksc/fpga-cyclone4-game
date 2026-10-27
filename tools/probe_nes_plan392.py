# SPDX-License-Identifier: MIT
"""390 live M4/SPI/IRQ/2slots/ROM with391 measured real65816 service.

Per-record native control and PPU events are measured CPU service allocations,
not a fullresident CPU lockstep. Cold905/906 retain the original consumer.
"""
import inspect,json,os,shutil
import probe_nes_increment389 as previous
import probe_nes_hint367 as hint
import nes_compact390 as compact
from nes_delta231 import ROOT,BASE,sha,once
from nes_source368 import compile_arm

NATIVE=BASE/'probes/nes-plan390/native01'
previous.NATIVE=NATIVE;previous.spool.NATIVE=NATIVE
old_profile=previous.old_profile
ps=inspect.getsource(old_profile).replace('overheads=[0]*5','overheads=[0]*7').replace("[first_poll-last_view,budget,len(rows)]+overheads", "[first_poll-last_view,budget,len(rows)]+overheads[:5]")
pn=dict(old_profile.__globals__,NATIVE=NATIVE);exec(compile(ps,'profile392','exec'),pn);previous.old_profile=pn['profile']
engine=previous.engine;old_prepare=engine.prepare;old_build=engine.build_rom

def build(d):
 old_build(d);shutil.copyfile(d/'output.elf',d/'pre390-output.elf');compact.arm(d);compile_arm(d)

old_worker_source=hint.worker_source
def worker_source():
 s,ns=old_worker_source();verify=ns['verify']
 s=once(s,'        rows.append(row);print(json.dumps(row),flush=True)',"        (d/'observed-stack390.json').write_text(json.dumps(dict(frame=f,observed=0x2003f000-arm.low_sp))+'\\n')\n        rows.append(row);print(json.dumps(row),flush=True)")
 def checked(pp,out):
  extra=[p for p in out if p[:2]==bytes([2,6])]
  serial=int.from_bytes(pp[0][4:8],'little');f=serial+904
  if f>=907:
   assert len(extra)==1,('compact plan count',f,len(extra))
   b=extra[0][16:];assert b==(NATIVE.parent/'arm01'/f'plan{f}.bin').read_bytes(),('real M4 plan mismatch',f)
  else:assert not extra
  # Check the real complete wire sequence first; normalize only the extra
  # packet's numbering gap for the unchanged legacy semantic comparator.
  for i,p in enumerate(out):assert int.from_bytes(p[2:4],'little')==i
  normalized=[]
  for p in out:
   if p[:2]==bytes([2,6]):continue
   q=bytearray(p);q[2:4]=len(normalized).to_bytes(2,'little');normalized.append(bytes(q))
  return verify(pp,normalized)
 ns['verify']=checked;return s,ns
hint.worker_source=worker_source

WARM=r'''
 task ordinary392;
 integer n392,head392,ignore392;reg [7:0] b392,desc392[0:8];reg [31:0] tok392;
 begin
  n392=dut.flow.qlen;head392=dut.flow.queue.consumed312;tok392=dut.flow.chunk_token;
  for(integer i=0;i<9;i++)rd261(24'h006060+i,desc392[i]);
  if({desc392[5],desc392[4]}!=dut.flow.chunk_length||desc392[1]!=dut.flow.header[1]||desc392[8]!={7'd0,~display_serial373[0]})$fatal(1,"native ordinary descriptor392");
  if(desc392[1]!=6)for(integer i=0;i<16;i++)begin
   if(i>=4&&i<=9)b392=i<8?dut.flow.identity[(i-4)*8+:8]:dut.flow.identity[32+(i-8)*8+:8];
   else if(i==2)b392=dut.flow.packet_seq[7:0]-1'b1;
   else if(i==3)b392=(dut.flow.packet_seq-1)>>8;
   else b392=dut.flow.header[i];
   ignore392=call263(1,i,b392);
  end
  store_begin384(desc392[1],{desc392[7],desc392[6]},dut.flow.chunk_length);
  #(records384[record384+1][63:40]*MASTER_NS378);
  for(integer i=0;i<dut.flow.chunk_length;i++)begin
   rd261(24'h400800+i,b392);store_byte384(b392);
   if(desc392[1]!=6&&i<n392-16)ignore392=call263(1,16+i,b392);
  end
  if(desc392[1]!=6)ignore392=call263(2,n392,0);
  // Native receipt reads the immutable32bit token after the actual data.
  for(integer i=0;i<4;i++)begin rd261(24'h006048+i,b392);if(b392!==tok392[i*8+:8])$fatal(1,"late native token392");wr261(24'h00604c+i,b392);end
  wr261(24'h006059,8'ha5);wait(dut.flow.queue.consumed312!=head392);ordinary263++;store_end384();
  // One native original command replaces exactly one legacy CPU trace case.
  // Retire that fixture's bookkeeping, while preserving its EOF guard. The
  // extra metadata has no legacy trace and must not consume one.
  if(desc392[1]!=6)begin
   if(cpu267[cpu_at267]<16)$fatal(1,"missing replaced legacy CPU case392");
   cpu_at267+=1+cpu267[cpu_at267];
  end
  $fwrite(events261,"ordinary392,%0d,%0d,%0d,%0t\n",f,desc392[1],dut.flow.chunk_length,$time);
 end endtask
'''

def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];compact.rtl(d);p=d/'joint266_tb.sv';s=p.read_text()
 s=once(s,' task ordinary_cpu267;',WARM+'\n task ordinary_cpu267;')
 # Only warm ordinary commands use the new real CPU service. The legacy
 # trace pointer is deliberately unused after the unchanged cold prefix.
 s=once(s,'  count267=cpu267[cpu_at267];', '  if(f>=907)begin ordinary392();return;end\n  count267=cpu267[cpu_at267];')
 p.write_text(s,newline='\n')
 for name in ('nes_compact390.py','nes_compact390.c','probe_nes_plan391.py','probe_nes_plan392.py'):shutil.copyfile(ROOT/'tools'/name,d/name)
 (d/'manifest392.json').write_text(json.dumps(dict(native=str(NATIVE),native_result=sha(NATIVE/'result.json'),ARM_changed=True,RTL_changed=True,
  legacy_ordinary_PPU_address_ports_retained_for_cold=True,source_receipt='WRAM storage',finalACK='After native PPU and VBlank display',scope=__doc__),indent=2)+'\n')
 return src,pins
engine.build_rom=build;engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
