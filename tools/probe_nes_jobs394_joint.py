# SPDX-License-Identifier: MIT
"""Actual M4/source/SPI/IRQ/ROM with common-record RTL and measured raw65816
bus service. Matching392 capture/start/ROM phase;not fullCPU lockstep/WCET."""
import argparse,csv,inspect,json,re,shutil,struct,subprocess,sys
from pathlib import Path
import probe_nes_plan392 as previous
from probe_nes_jobs394_arm import decode
from probe_nes_jobs394_native import current_view
from probe_nes_arm264 import plans,u16
from analyze_nes_jobs393 import source_bits
from nes_delta231 import ROOT,BASE,sha
from nes_jobs394 import arm as apply_arm,rtl as apply_rtl
from nes_source368 import compile_arm
from probe_nes_refill267 import run

NATIVE=BASE/'probes/nes-jobs394/native04'

class Live394(previous.hint.Live367):
 def exchange(self,tx):
  symbol=self.arm.symbols.get('wire_busy394');owned=int.from_bytes(self.arm.uc.mem_read(symbol,4),'little')if symbol else 0
  value=super().exchange(tx);self.transfers[-1]['wire_owned394']=owned;return value

def verify(pp,out):
 serial=int.from_bytes(pp[0][4:8],'little');oracle,_=plans();expected=(oracle/f'expected-{serial}.bin').read_bytes();bits,required=source_bits(pp,expected)
 for i,p in enumerate(out):assert u16(p,2)==i and int.from_bytes(p[4:8],'little')==serial and len(p)==10+u16(p,8)
 jobs=decode(out);seen=set();refs=set()
 for j in jobs:
  r=bytes.fromhex(j['record']);data=bytes.fromhex(j['payload']);region=r[9];first=u16(r,10)
  if r[6]&16:assert region in(3,4)and region not in refs and not data;refs.add(region);continue
  if region==2:
   for i in range(len(data)//2):
    w=first+i*(32 if r[8]==0x81 else 1);assert w in required and w not in seen;seen.add(w);assert data[2*i:2*i+2]==expected[2*w:2*w+2]
  elif region>=3:
   if r[6]&64:assert region==5 and first==21 and u16(r,4)==1100 and data==b'\0\0'
   else:assert data==expected[(4096 if region==3 else 4608 if region==4 else 5152)+first:][:len(data)]
 assert seen==required and out[-1][0]==0xa3

def worker(d,last,irq=False,rom=False):
 s,ns=previous.old_worker_source();ns['verify']=verify
 old=previous.hint.worker_source;old_live=previous.hint.Live367;previous.hint.worker_source=lambda:(s,ns);previous.hint.Live367=Live394
 try:return previous.hint.worker(d,last,irq,rom)
 finally:previous.hint.worker_source=old;previous.hint.Live367=old_live

def profile(d,f):
 q=NATIVE/str(f);jobs=json.loads((q/'fixture.json').read_text());ev=[list(map(int,x))for x in csv.reader((q/'events.csv').read_text().splitlines())];tm=list(csv.DictReader((q/'timings.csv').read_text().splitlines()))
 first={i:next(x[4]for x in ev if x[0]==i and x[1:3]==[0,0x6001])for i in range(1,len(jobs)+2)}
 # Reuse the exact realCPU bus events per source fragment;do not add the
 # measured control time again on top of its descriptor/token reads.
 words=[];payload=bytearray();desc=bytearray()
 for i,j in enumerate(jobs,1):
  events=[x for x in ev if x[0]==i and first[i]<=x[4]<first[i+1]]
  assert events[-1][1:4]==[1,0x6050,0xa5]
  words.append(len(events));words.extend(((x[4]-first[i])<<40)|(x[1]<<32)|(x[2]<<8)|x[3]for x in events)
  b=bytes.fromhex(j['data']);payload+=b;desc+=bytes.fromhex(j['record'])+struct.pack('<HHB',j['offset'],len(b),int(j['first'])+2*int(j['last']))
 words.append(0)
 last_view=max(x[4]for x in ev if x[1]==0 and 0x6070<=x[2]<=0x607b)
 first_poll=next(x[4]for x in ev if x[1:3]==[0,0x4212]and x[4]>last_view)
 first_ppu=next(int(x['clock'])for x in tm if x['phase']=='PPU_trigger')
 last_ppu=max(int(x['clock'])for x in tm if x['phase']=='PPU_done')
 origin=max(x[4]for x in ev if x[1:3]==[0,0x4212]and x[4]<first_ppu)if f>=907 else last_view
 tail=[x for x in ev if x[4]>origin]
 if f<907:
  # Cold initialization is forcedblank. Split off the wait for the final
  # legal display window;its arbitrary fixture wait is not replayed as work.
  after=max(x[4]for x in ev if x[1:3]==[0,0x4212]and x[4]<ev[-1][4]);tail=[x for x in ev if origin<x[4]<=last_ppu]+[x[:4]+[last_ppu+(x[4]-after)]+x[5:]for x in ev if x[4]>after]
  split=sum(x[4]<=last_ppu for x in tail)
 else:split=0
 assert tail[-1][1:4]==[1,0x6058,0x5a]
 body_budget=3840
 for j in jobs:
  r=bytes.fromhex(j['record'])
  if j['first']and r[6]&3!=3:body_budget+=8*u16(r,4)+(1200 if r[6]&3==0 else 1408)
 cutoff=246 if body_budget<20001 else 238 if body_budget<30001 else 230 if body_budget<40001 else 225
 cfg=[first[1],first_poll-last_view if f>=907 else 0,tail[-1][4]-origin+512,len(tail),cutoff,split,len(jobs)]
 for name,data,width in [('source',words,16),('data',payload,2),('desc',desc,2),('tail',[len(tail)]+[((x[4]-origin)<<40)|(x[1]<<32)|(x[2]<<8)|x[3]for x in tail],16),('config',cfg,16)]:
  (d/f'jobs394-{name}{f}.hex').write_text('\n'.join(f'{v:0{width}x}'for v in data)+'\n',newline='\n')
 (d/f'jobs394-view{f}.hex').write_text('\n'.join(f'{b:02x}'for b in current_view(f))+'\n')
 return dict(frame=f,events=sha(q/'events.csv'),native=sha(q/'spool.sfc'),config=cfg)

TASKS=r'''
 reg [63:0] source394[0:32767],tail394[0:16383],config394[0:6];reg [7:0] expected394[0:32767],desc394[0:8191],view394[0:11];
 integer source_at394=0,stored394=0,data_at394=0;
 task reset394;begin
  $readmemh($sformatf("jobs394-source%0d.hex",f),source394);$readmemh($sformatf("jobs394-data%0d.hex",f),expected394);$readmemh($sformatf("jobs394-desc%0d.hex",f),desc394);
  $readmemh($sformatf("jobs394-tail%0d.hex",f),tail394);$readmemh($sformatf("jobs394-config%0d.hex",f),config394);
  $readmemh($sformatf("jobs394-view%0d.hex",f),view394);
  source_at394=0;stored394=0;data_at394=0;
 end endtask
 task source_job394;
 integer n,j,reads,header_at,position394,base394;reg [63:0] e;reg [23:0] a;reg [7:0] b;reg [31:0] token;realtime origin;
 begin
  if(source394[source_at394]==0)$fatal(1,"extra common source job394");
  n=source394[source_at394];source_at394++;reads=0;header_at=0;token=dut.flow.chunk_token;origin=$realtime;
  for(j=0;j<n;j++)begin
   e=source394[source_at394];source_at394++;until378(origin+e[63:40]*MASTER_NS378);a=e[31:8];b=e[7:0];
   if(test_abort||source_fault||flow_fault)return;
   if(a>=24'h006000)begin
    if(a>=24'h006048&&a<=24'h00604f)b=token[a[1:0]*8+:8];
    if(e[32])wr261(a,b);
    else begin
     rd261(a,b);
     if(a>=24'h006080&&a<=24'h006090)begin
      if(b!==desc394[stored394*17+a-24'h006080])$fatal(1,"live common record394 f%0d job%0d field%0d got%h expected%h",f,stored394,a-24'h006080,b,desc394[stored394*17+a-24'h006080]);header_at++;
     end else if(a>=24'h400800)begin end
     else if(a==24'h006001&&b[7])return;
    end
   end else if(e[32])begin
    if(a==24'h002100&&f<907)ppu378[a]=b;
   end
   // Source aperture addresses are outside the control register interval.
   if(a>=24'h400800&&a<24'h401800)begin
    if(e[32])$fatal(1,"native source write394");
    // The register branch above already executes this actual read.
    if(b!==expected394[data_at394+reads])$fatal(1,"live common payload394 f%0d job%0d byte%0d",f,stored394,reads);
    if(dut.flow.region>=2)begin
     position394=dut.flow.region==2?2*(dut.flow.canonical+((dut.flow.fragment_at+reads)/2)*(dut.flow.stride32?32:1))+((dut.flow.fragment_at+reads)%2):dut.flow.canonical+dut.flow.fragment_at+reads;
     base394=dut.flow.region==2?0:dut.flow.region==3?4096:dut.flow.region==4?4608:5152;
     if(b!==expected263[base394+position394])$fatal(1,"independent canonical value394 region%0d position%0d",dut.flow.region,position394);
    end
    reads++;dmabytes263++;
   end
  end
  if(header_at!=17)$fatal(1,"missing raw record394");
  wait(!staged);data_at394+=reads;stored394++;ordinary263++;
  $fwrite(events261,"stored394,%0d,%0d,%0d,%0t\n",f,stored394,reads,$time);
 end endtask
 task display_job394;
 integer window,scroll,split;reg [63:0] e;reg [23:0] a;reg [7:0] b;reg [31:0] token;realtime origin;
 begin
  if(stored394!=config394[6])$fatal(1,"PPU before all source jobs394");
  token=dut.flow.fence;
  // Exact12 view reads;these also validate current frame/H2 meaning.
  for(integer i=0;i<12;i++)begin wait(dut.flow.state==dut.flow.DVIEW);rd261(24'h006070+i,b);if(b!==view394[i])$fatal(1,"live view394");end
  check_final265();#(config394[1]*MASTER_NS378);
  if(f>=907)while(!blank378()||phase378()/1364>config394[4]||357368-phase378()<config394[2])begin #(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;end
  origin=$realtime;window=(romcycle267+SNES_PHASE378)/357368;scroll=0;split=config394[5];
  $fwrite(events261,"vblank394,%0d,%0t,%0d,%0d\n",f,$time,phase378(),window);
  for(integer i=1;i<=tail394[0];i++)begin
   e=tail394[i];until378(origin+e[63:40]*MASTER_NS378);a=e[31:8];b=e[7:0];
   if(source_fault||flow_fault||test_abort)return;
   if(f>=907&&!blank378())$fatal(1,"PPU left VBlank394");
   if(f<907&&i==split+1)begin
    while(!blank378())begin #(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;end
    origin=$realtime-e[63:40]*MASTER_NS378;window=(romcycle267+SNES_PHASE378)/357368;
   end
   if(a>=24'h006000)begin
    if(a>=24'h006048&&a<=24'h00604f)b=token[a[1:0]*8+:8];
    if(e[32])wr261(a,b);else begin rd261(a,b);if(a==24'h006001&&b[7:6])return;end
   end else if(e[32])begin
    if(a==24'h00210d||a==24'h00210e)begin if(scroll>=4||b!==view394[8+scroll])$fatal(1,"live scroll394");scroll++;end
    ppu378[a]=b;$fwrite(events261,"ppu394,%0d,%0d,%0d,%0t,%0d\n",f,a,b,$time,phase378());
   end
  end
  if(scroll!=4||ppu378[16'h2100]!=15)$fatal(1,"final PPU state394");
  $fwrite(events261,"present394,%0d,%0t,%0d,%0d\n",f,$time,window,phase378());wait(!v_sealed);
 end endtask
 initial begin : bus394
  bus_read=1;bus_write=1;bus_address=0;bus_in=0;
  forever begin
   @(negedge host_clk);
   if(active263)begin
    if(staged)source_job394();
    else if(v_sealed&&dut.flow.state==dut.flow.DVIEW)display_job394();
   end
  end
 end
'''

def adapt_tb(s):
 s=s.replace("  repeat(20)@(negedge host_clk);wr261(24'h006006,8'ha5);\n  wait(!dut.flow.invalidate_banks);",'  // Actual native startup writes the invalidate ACK;no fixture ACK.')
 s=s.replace('dut.flow.tap_state278','dut.flow.read_pending').replace('dut.flow.packet_seq','dut.flow.allocation')
 s=re.sub(r'(?m)^   for\(integer i=0;i<8570;i\+\+\)if\(call263.*?\n','',s)
 # Remove obsolete test-only observers and tasks rather than adding legacy
 # fields/ports back to the new synthesized implementation.
 tasks=list(re.finditer(r'(?m)^ task\s+(\w+)\b.*?endtask',s,re.S))
 keep={'rd261','wr261','token261','tiles_task263','check_final265','until378','transfer','shift367'}
 for m in reversed(tasks):
  if m[1]not in keep:s=s[:m.start()]+s[m.end():]
 # One old helper is a test fixture consumer and has no implementation value.
 for name in ('negative261','abort_prelude262','negative_prelude262','bus263'):
  pat=re.compile(r'(?m)^ initial begin : '+name+r'\b')
  m=pat.search(s)
  if m:
   end=block_end(s,m.start());s=s[:m.start()]+s[end:]
 positions=list(re.finditer(r'(?m)^ always\b',s))
 for m in reversed(positions):
  end=block_end(s,m.start());part=s[m.start():end]
  if 'dut.flow.'in part:s=s[:m.start()]+s[end:]
 s=s.replace('  bus_read=1;bus_write=1;bus_address=0;bus_in=0;','  bus_read=1;bus_write=1;bus_address=0;bus_in=0;')
 # Driver entry. Tile bytes still come from the actual ROM+arbiter,not jobs.
 task=''' task output_frame;
 begin
  $readmemh($sformatf("meta%0d.hex",f),expected263);$readmemh($sformatf("tiles%0d.hex",f),tiles263);$readmemh($sformatf("tiles%0d.lens",f),tile_sizes263);$readmemh($sformatf("prelude%0d.hex",f),prelude262);
  tile_at267=0;reset394();active263=1;tiles_task263();wait(arm_done_frame367>=f);wait(retired_count368>=f-904);@(negedge clk);active263=0;frames263++;
 end endtask
'''
 guard=r'''
 always @(posedge host_clk)if(!reset&&active263)begin
  if($isunknown({dut.core.validator.checksum,dut.core.validator.digest,dut.core.validator.fault}))$fatal(1,"unknown independent CRC394");
  if(flow_fault||lease_fault)$fatal(1,"new common flow fault394 state%0d checker%0d",dut.flow.state,dut.core.validator.fault);
  if(dut.source_selected&&dut.output_selected)$fatal(1,"shared SPI double owner394");
  if(dut.flow.queue.used>2)$fatal(1,"two-slot overflow394");
  if(dut.flow.consume_record312&&(!dut.flow.ready359||dut.flow.read_pending))$fatal(1,"receipt before actual read drain394");
  if(dut.flow.ordinary_finish&&(!dut.flow.jobs_committed336))$fatal(1,"seal before source drain394");
 end
'''
 s=s.replace(' initial begin : query_cancel',guard+TASKS+'\n'+task+'\n initial begin : query_cancel')
 # New guards cover the retained invariants in the actual new state names.
 s=s.replace(' task clear_output;',r'''
 always @(posedge host_clk)if(!reset&&active263)begin
  if(flow_fault||lease_fault)$fatal(1,"new common flow fault394 state%0d checker%0d",dut.flow.state,dut.core.validator.fault);
  if(dut.source_selected&&dut.output_selected)$fatal(1,"shared SPI double owner394");
  if(dut.flow.queue.used>2)$fatal(1,"two-slot overflow394");
  if(dut.flow.consume_record312&&(!dut.flow.ready359||dut.flow.read_pending))$fatal(1,"receipt before actual read drain394");
  if(dut.flow.ordinary_finish&&(!dut.flow.jobs_committed336))$fatal(1,"seal before source drain394");
 end
 task clear_output;''')
 return s

def block_end(s,start):
 # begin/end token matching,excluding strings/comments. All requested
 # constructs are procedural blocks or one semicolon statement.
 token=re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\bbegin\b|\bend\b|;',re.S);level=0;entered=False
 for m in token.finditer(s,start):
  t=m[0]
  if t.startswith(('//','/*','"')):continue
  if t=='begin':level+=1;entered=True
  elif t=='end':
   level-=1
   if entered and not level:return m.end()
  elif not entered:return m.end()
 raise AssertionError('unclosed test construct')

def prepare(d,last,cold_quantum=0):
 d.mkdir(parents=True,exist_ok=False);reference=BASE/'probes/nes-plan390/joint04'
 suffixes={'.sv','.c','.h','.inc','.s','.a','.ld','.hex','.lens','.desc','.cfg','.bin','.expected','.palette'}
 for f in reference.iterdir():
  if f.is_file()and f.suffix in suffixes:shutil.copyfile(f,d/f.name)
 for f in range(905,last+1):
  for suffix in('.hex','.expected','.palette'):assert(d/f'frame{f}{suffix}').is_file()
 apply_arm(d,cold_quantum);apply_rtl(d);compile_arm(d)
 s=adapt_tb((d/'joint266_tb.sv').read_text());(d/'joint266_tb.sv').write_text(s,newline='\n')
 profiles=[profile(d,f)for f in range(905,last+1)]
 # Match the392 compiled sources,replace only the common boundary.
 r=json.loads((reference/'result.json').read_text())if(reference/'result.json').exists()else None
 command=next(x for x in(reference/'vlog.log').read_text().splitlines()if x.startswith('vlog -sv '))
 src=[n for n in command.split()[2:]if n!='joint266_tb.sv'and n not in('nes_tile_producer260.sv','nes_host_context375.sv')]+['nes_tile_link394.sv']
 (d/'manifest394.json').write_text(json.dumps(dict(scope=__doc__,profiles=profiles,materialized_RTL={n:sha(d/n)for n in src},ELF=sha(d/'output.elf'),test=sha(d/'joint266_tb.sv')),indent=2)+'\n')
 return src

def main():
 global NATIVE
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--last',type=int,default=916);p.add_argument('--worker',action='store_true');p.add_argument('--cold-quantum',type=int,choices=(0,256),default=0);p.add_argument('--native',type=Path);a,extra=p.parse_known_args();assert all(x in('--keep-source','--early-release')for x in extra);d=a.out.resolve()
 if a.cold_quantum and not a.native and not a.worker:p.error('cold256 requires freshly generated matching --native profiles;historical native03 predates CPU startup ACK')
 NATIVE=a.native.resolve()if a.native else BASE/'probes/nes-jobs394/native04'
 if a.worker:return worker(d,a.last,True,True)
 src=prepare(d,a.last,a.cold_quantum);q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer264.c','nes_bridge267.c','-o','producer263.dll'],d,'native')
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*src,'joint266_tb.sv'],d,'vlog')
 with(d/'arm-worker.log').open('wb')as log:
  child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker','--out',str(d),'--last',str(a.last),'--cold-quantum',str(a.cold_quantum)],cwd=d,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   result=run(q/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb','-gCPI=1','-gROM_WINDOW=1',f'+LAST={a.last}','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',1800)
   assert f'PASS REFILL267 frames={a.last-904}'in result;assert child.wait(timeout=10)==0
  finally:
   if child.poll()is None:child.kill();child.wait()
 (d/'result.json').write_text(json.dumps(dict(passed=True,frames=a.last-904,scope=__doc__,ELF=sha(d/'output.elf'),RTL={n:sha(d/n)for n in src}),indent=2)+'\n')
 print('PASS JOINT394',a.last-904)
if __name__=='__main__':main()
