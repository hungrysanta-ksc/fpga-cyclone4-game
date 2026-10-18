# SPDX-License-Identifier: MIT
"""Execute receipt core on recorded ranges/manifests; MAP with tested249 source.

Joint synthesis is a shared-clock module envelope, not a connected parser,
collector/query, SPI FIFO arbiter or full-board implementation.
"""
from pathlib import Path
import argparse,csv,json,re,subprocess,shutil,os
from nes_delta231 import ROOT,BASE,sha
from nes_receipt250 import RTL
from nes_block249_rtl import RTL as SOURCE
from analyze_nes_spantrade247 import spans
from analyze_nes_mapjoint247 import bitmap
from analyze_nes_joint249 import mark,coverage,map_receipt

TB=r'''
`timescale 1ns/1ps
module receipt250_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort_source=0,begin_valid=0,target_bank=0,range_valid=0,map_range=0,check_valid=0,finish_valid=0,all_consumed=0,display_ack=0;
 reg [2:0] raw_count=0;reg [11:0] first=0,count=0;reg [7:0] check_value=0;
 wire ready,sealed;wire [3:0] fault;
 nes_receipt250 dut(.*);
 reg [63:0] cmds[0:100000];reg [7:0] expected[0:71*754-1];
 integer at=0,op,fd,tick=0,started=0,frame=0,guards=0;reg [63:0] c;
 always @(posedge clk)tick++;
 task pulse_clear;
 begin begin_valid=0;range_valid=0;check_valid=0;finish_valid=0;display_ack=0;abort_source=0;end
 endtask
 initial begin
  $readmemh("commands.hex",cmds);$readmemh("expected.hex",expected);
  fd=$fopen("cycles.csv","w");$fwrite(fd,"frame,cycles\n");
  repeat(3)@(negedge clk);reset=0;wait(ready);
  while(1)begin
   c=cmds[at];op=c[63:60];at++;
   if(op==15)begin $display("PASS RECEIPT250 frames=%0d guards=%0d",frame,guards);$fclose(fd);$finish;end
   if(op==8)begin @(negedge clk);pulse_clear();reset=1;repeat(3)@(negedge clk);reset=0;wait(ready);end
   else if(op==9)begin repeat(3)@(negedge clk);if(fault!==c[3:0]||ready||sealed)$fatal(1,"fault guard at=%0d expected=%0d got=%0d",at,c[3:0],fault);guards++;end
   else if(op==10||op==12)begin
    wait(ready);for(integer i=148;i<166;i++)begin
     if(dut.memory[i]!==((op==12)?8'hff:8'h00)||dut.memory[i+166]!==((op==12)?8'hff:8'h00))$fatal(1,"raw transition op%0d at%0d",op,i);
    end
    guards++;
   end else if(op==7)begin
    if(!sealed||fault)$fatal(1,"no seal at frame%0d",frame);
    for(integer i=0;i<754;i++)if(dut.memory[i]!==expected[frame*754+i])$fatal(1,"RAM frame%0d at%0d",frame,i);
    $fwrite(fd,"%0d,%0d\n",frame+905,tick-started);frame++;
   end else begin
    if(op!=5&&op!=6)begin if(fault)$fatal(1,"unexpected fault %0d at%0d",fault,at);wait(ready);end
    @(negedge clk);pulse_clear();
    case(op)
     1:begin begin_valid=1;target_bank=c[0];raw_count=c[6:4];started=tick;end
     2:begin range_valid=1;map_range=c[32];first=c[23:12];count=c[11:0];end
     3:begin check_valid=1;check_value=c[7:0];end
     4:begin finish_valid=1;all_consumed=c[0];end
     5:display_ack=1;
     6:abort_source=1;
     default:$fatal(1,"bad command");
    endcase
    @(negedge clk);pulse_clear();
    if(op==1||op==2||op==3)begin
     if(cmds[at][63:60]!=9)begin wait(ready||fault);if(fault)$fatal(1,"operation failed %0d at%0d",fault,at);end
    end
   end
  end
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
'''

def joint():
 sh=re.search(r'module nes_source_block249\((.*?)\);',SOURCE,re.S).group(1)
 vh=re.search(r'module nes_receipt250\((.*?)\);',RTL,re.S).group(1)
 names=lambda h:[re.search(r'(\w+)\s*$',s).group(1) for s in h.split(',')]
 sn=names(sh);vn=names(vh);shared={'clk','reset','abort_source'}
 vh=re.sub(r'input wire clk,reset,abort_source,','',vh)
 for name in sorted(set(vn)-shared,key=len,reverse=True):vh=re.sub(r'\b'+name+r'\b','v_'+name,vh)
 return 'module nes_joint250('+sh+','+vh+');\nnes_source_block249 encoder('+','.join('.'+n+'('+n+')' for n in sn)+');\nnes_receipt250 validator('+','.join('.'+n+'('+(n if n in shared else 'v_'+n)+')' for n in vn)+');\nendmodule\n'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path);p.add_argument('--map-test',type=Path);a=p.parse_args()
 d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True);pins={}
 def pin(f):f=f.resolve();pins[f.relative_to(BASE).as_posix()]=sha(f);return f
 def run(exe,args,label):
  with (d/(label+'.log')).open('wb') as log:q=subprocess.run([str(exe),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(d/(label+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4500:];return s
 for name,s in [('nes_receipt250.sv',RTL),('nes_source_block249.sv',SOURCE),('nes_joint250.sv',joint())]:(d/name).write_text(s,encoding='utf-8',newline='\n')
 shutil.copyfile(__file__,d/'probe.py');shutil.copyfile(ROOT/'tools/nes_receipt250.py',d/'nes_receipt250.py')
 if a.map_test:
  test=json.loads(pin(a.map_test/'result.json').read_text());assert test['passed'] and test['rtl_sha256']==sha(d/'nes_receipt250.sv')
  source=json.loads(pin(BASE/'probes/nes-joint249/blocktest03/result.json').read_text());assert source['passed'] and source['encoder_sha256']==sha(d/'nes_source_block249.sv')
  (d/'joint.qpf').write_text('PROJECT_REVISION = "joint"\n')
  (d/'joint.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_joint250','set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',*[f'set_global_assignment -name SYSTEMVERILOG_FILE {n}' for n in ('nes_receipt250.sv','nes_source_block249.sv','nes_joint250.sv')]])+'\n')
  run('C:/altera_standard/25.1std/quartus/bin64/quartus_map.exe',['joint'],'map')
  summary=(d/'output_files/joint.map.summary').read_text();report=(d/'output_files/joint.map.rpt').read_text()
  result=dict(passed=True,summary=summary,hierarchy=[s.strip() for s in report.splitlines() if re.match(r';\s*\|nes_(source_block249:encoder|receipt250:validator)\|',s)],ram_rows=[s.strip() for s in report.splitlines() if 'M9K' in s and ('base_' in s or 'scratch' in s or 'memory' in s)],fit=False,parser=False,query=False,CDC=False)
  print(summary)
 else:
  assert a.questa_bin and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
  prior=BASE/'probes/nes-wholepath247';ranges={g:[] for g in range(1,72)}
  for r in csv.DictReader(pin(prior/'validation-test02/run/range247.csv').open()):ranges[int(r['generation'])].append({k:int(v) for k,v in r.items()})
  seals={}
  for f in sorted((prior/'jointdecode-test02/run').glob('req-*.bin')):
   b=pin(f).read_bytes()
   if b[0]==3:seals[int.from_bytes(b[8:10],'little')]=b
  ram=bytearray(1024);previous=bytes(4096);stale=[set(range(2048)),set(range(2048))];commands=[];expected=bytearray()
  def cmd(op,v=0):commands.append((op<<60)|v)
  for g in range(1,72):
   bank=(g-1)%2;seal=seals[g];raw=int.from_bytes(seal[38:40],'little');cmd(1,bank|(raw<<4));ram[332:754]=bytes(422)
   for r in ranges[g]:cmd(2,(r['start']<<12)|r['take']);mark(ram,bank,r['start'],r['take'])
   current=pin(prior/f'jointdecode-test02/run/expected-{g}.bin').read_bytes()[:4096]
   change={i for i in range(2048) if current[2*i:2*i+2]!=previous[2*i:2*i+2]}
   for st in stale:st.update(change)
   rr=spans(stale[bank],16,64);map_receipt(ram,rr)
   for at,n in rr:cmd(2,(1<<32)|((at//2)<<12)|(n//2))
   coverage(ram,bank,seal)
   for v in seal[40:184]+seal[184:206]+bytes(ram[498:754]):cmd(3,v)
   if g==1:first_frame=list(commands)
   cmd(4,1);cmd(7);cmd(5);expected+=ram[:754];stale[bank].clear();previous=current
  # Recorded scroll has raw_count2 throughout; explicitly test normal entry.
  cmd(12);cmd(1,0);cmd(10)
  # Faults are followed by reset; no speculative frame can be published.
  cases=[[(1,0),(2,0),(9,2)],[(1,0),(2,(1327<<12)|2),(9,2)],[(1,0),(2,(1<<32)|(2047<<12)|2),(9,2)],
         [(1,0),(2,1),(2,1),(9,2)],[(1,0),(4,1),(9,3)],[(1,0),(5,0),(9,5)],[(1,0),(6,0),(9,4)],
         [(1,0),(3,1),(9,3)]]
  for case in cases:cmd(8);[cmd(op,v) for op,v in case]
  cmd(8);commands.extend(first_frame);cmd(4,0);cmd(9,3)
  # Omit first map range at cold start, then present its expected manifest.
  cmd(8);skipped=False;checks=0
  for v in first_frame:
   if v>>60==2 and (v>>32)&1 and not skipped:skipped=True;continue
   commands.append(v)
   if v>>60==3:
    checks+=1
    if checks==167:break
  cmd(9,3)
  cmd(15);(d/'commands.hex').write_text('\n'.join(f'{v:016x}' for v in commands)+'\n');(d/'expected.hex').write_text(expected.hex(' '));(d/'receipt250_tb.sv').write_text(TB)
  run(a.questa_bin/'vlib.exe',['work'],'vlib');run(a.questa_bin/'vlog.exe',['-sv','nes_receipt250.sv','receipt250_tb.sv'],'vlog')
  s=run(a.questa_bin/'vsim.exe',['-c','work.receipt250_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'vsim');assert 'PASS RECEIPT250 frames=71 guards=12' in s
  result=dict(passed=True,frames=71,guards=12,memory_bytes_checked=len(expected),commands=len(commands),rtl_sha256=sha(d/'nes_receipt250.sv'),parser=False,query=False,CDC=False,certificate_binding=False)
  print(json.dumps(result))
 result.update(scope=__doc__,input_hashes=pins,script_sha256=sha(Path(__file__)))
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
