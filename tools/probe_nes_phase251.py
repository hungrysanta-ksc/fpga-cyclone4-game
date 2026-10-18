# SPDX-License-Identifier: MIT
"""Phase RAM experiment: parsed fixture interfaces, not a packet/CDC binding."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_delta231 import ROOT,BASE,sha,once
from nes_phase251 import sources
from probe_nes_source249 import TB

EXTRA=r'''
 reg v_begin_valid=0,v_target_bank=0,v_range_valid=0,v_map_range=0,v_check_valid=0,v_finish_valid=0,v_all_consumed=0,v_display_ack=0;
 reg [2:0] v_raw_count=0;reg [11:0] v_first=0,v_count=0;reg [7:0] v_check_value=0;
 wire v_ready,v_sealed;wire [3:0] v_fault;
 reg [63:0] cmds[0:100000];reg [7:0] receipt_expected[0:71*754-1],persistent[0:331];
 integer at=0,op,rf=0,rt,rfstarted,trial,guard_mode=0;reg [63:0] c;
 reg [7:0] stopped[0:1023];
 task clear_v;
 begin v_begin_valid=0;v_range_valid=0;v_check_valid=0;v_finish_valid=0;v_display_ack=0;end
 endtask
 task stop_output;
 begin
  @(negedge clk);abort_source=1;@(negedge clk);abort_source=0;
  repeat(2)@(negedge clk);
  if(fault!=4||start_ready||v_ready||v_sealed||dut.encoder.base_valid)$fatal(1,"output STOP lifetime");
  for(integer j=0;j<1024;j++)stopped[j]=dut.memory[j];
  repeat(10)@(negedge clk);
  for(integer j=0;j<1024;j++)if(stopped[j]!==dut.memory[j])$fatal(1,"write after STOP");
 end
 endtask
 task output_frame;
 begin
  op=0;
  while(op!=5)begin
   c=cmds[at];op=c[63:60];at++;
   if(start_ready||!dut.out_phase)$fatal(1,"source/output ownership");
   if(op==7)begin
    if(!v_sealed||fault)$fatal(1,"seal");
    for(integer j=0;j<754;j++)if(dut.memory[j]!==receipt_expected[rf*754+j])$fatal(1,"receipt RAM frame%0d at%0d",rf,j);
    $fwrite(rt,"%0d,%0d\n",f,tick-rfstarted);rf++;
    if(guard_mode==2)begin stop_output();return;end
   end else begin
    if(op!=5)wait(v_ready);
    @(negedge clk);clear_v();
    if(op==1&&guard_mode==1)begin stop_output();return;end
    if(op==1)begin
     // A next-source request is backpressured until final display ACK.
     start=1;repeat(3)@(negedge clk);start=0;
     if(dut.encoder.state!=dut.encoder.IDLE||start_ready)$fatal(1,"early source accepted");
    end
    case(op)
     1:begin v_begin_valid=1;v_target_bank=c[0];v_raw_count=c[6:4];rfstarted=tick;end
     2:begin v_range_valid=1;v_map_range=c[32];v_first=c[23:12];v_count=c[11:0];end
     3:begin v_check_valid=1;v_check_value=c[7:0];end
     4:begin v_finish_valid=1;v_all_consumed=c[0];end
     5:v_display_ack=1;
     default:$fatal(1,"unexpected receipt opcode");
    endcase
    @(negedge clk);clear_v();
    if(op==1||op==2||op==3)begin wait(v_ready||fault);if(fault)$fatal(1,"receipt fault");end
   end
  end
  wait(start_ready);
 end
 endtask
 always @(posedge clk)if(!reset&&!abort_source&&!fault)begin
  if(dut.out_phase&&(dut.saw||dut.sbw||start_ready))$fatal(1,"source write in output phase");
  if(dut.initialized&&!dut.out_phase&&dut.vw)$fatal(1,"validator write in source phase");
  if(dut.aw&&dut.bw&&dut.aa==dut.ba)$fatal(1,"shared collision");
 end
'''

def testbench():
 t=TB.replace('nes_source_encoder249','nes_phase251')
 t=re.sub(r'dut\.', 'dut.encoder.',t)
 t=once(t,' nes_phase251 dut(',EXTRA+'\n nes_phase251 dut(')
 ports=['begin_valid','target_bank','raw_count','range_valid','map_range','first','count','check_valid','check_value','finish_valid','all_consumed','display_ack','ready','sealed','fault']
 t=once(t,'.done(done),.fault(fault));','.done(done),.fault(fault),'+','.join('.v_'+n+'(v_'+n+')' for n in ports)+');')
 t=once(t,'  fd=$fopen', '  $readmemh("commands.hex",cmds);$readmemh("expected.hex",receipt_expected);\n  rt=$fopen("receipt-cycles.csv","w");$fwrite(rt,"frame,cycles\\n");\n  fd=$fopen')
 t=once(t,'   wait(start_ready);@(negedge clk);start=1;', '   wait(start_ready);for(integer j=0;j<332;j++)persistent[j]=dut.memory[j];\n   @(negedge clk);start=1;')
 t=once(t,'   if(seen!=total_expected', '   for(integer j=0;j<332;j++)if(dut.memory[j]!==persistent[j])$fatal(1,"persistent validity clobbered");\n   if(seen!=total_expected')
 t=once(t,'   @(negedge clk);generation++;serial++;','   output_frame();\n   @(negedge clk);generation++;serial++;')
 t=once(t,'reset=0;serial=2;', 'reset=0;serial=2;wait(start_ready);')
 t=once(t,'for(f=905;f<=975;f++)begin','for(trial=0;trial<73;trial++)begin\n   guard_mode=trial<71?0:trial-70;f=905+(trial%71);\n   if(guard_mode)begin reset=1;repeat(3)@(negedge clk);reset=0;generation=1;serial=1;rf=0;at=0;end')
 # Directed replay uses first-frame receipt and source fixtures after reset.
 t=once(t,'guard_mode=trial<71?0:trial-70;f=905+(trial%71);','guard_mode=trial<71?0:trial-70;f=guard_mode?905:905+trial;')
 t=t.replace('if(fault&&f<=975)', 'if(fault&&f<=975&&!guard_mode)')
 t=t.replace('PASS SOURCE249 frames=71 abort_and_cold_guards=2','PASS PHASE251 frames=71 directed_replays=2 persistent_bytes=24236 receipt_bytes=54288 guards=4')
 return t

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path);p.add_argument('--map-test',type=Path);a=p.parse_args()
 d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True);pins={}
 def pin(f):f=f.resolve();pins[f.relative_to(BASE).as_posix()]=sha(f)
 def run(exe,args,label):
  with (d/(label+'.log')).open('wb') as log:q=subprocess.run([str(exe),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(d/(label+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-6000:];return s
 for n,s in sources().items():(d/n).write_text(s,encoding='utf-8',newline='\n')
 for n in ('nes_phase251.py','probe_nes_phase251.py'):shutil.copyfile(ROOT/'tools'/n,d/n)
 hashes={n:sha(d/n) for n in sources()}
 if a.map_test:
  pin(a.map_test/'result.json');old=json.loads((a.map_test/'result.json').read_text());assert old['passed'] and hashes==old['rtl_hashes']
  (d/'phase.qpf').write_text('PROJECT_REVISION = "phase"\n')
  (d/'phase.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_phase251','set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',*[f'set_global_assignment -name SYSTEMVERILOG_FILE {n}' for n in sources()]])+'\n')
  run('C:/altera_standard/25.1std/quartus/bin64/quartus_map.exe',['phase'],'map')
  report=(d/'output_files/phase.map.rpt').read_text();summary=(d/'output_files/phase.map.summary').read_text()
  result=dict(passed=True,summary=summary,ram_rows=[l.strip() for l in report.splitlines() if 'M9K' in l and ('base_' in l or 'memory' in l)],fit=False,sta=False);print(summary)
 else:
  assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
  for f in (BASE/'probes/nes-joint249/blocktest03').glob('frame*'):
   if int(f.name[5:8])<=975:pin(f);shutil.copyfile(f,d/f.name)
  for n in ('commands.hex','expected.hex'):
   f=BASE/'probes/nes-joint250/receipt02'/n;pin(f);shutil.copyfile(f,d/n)
  (d/'phase_tb.sv').write_text(testbench(),newline='\n')
  run(a.questa_bin/'vlib.exe',['work'],'vlib');run(a.questa_bin/'vlog.exe',['-sv',*sources(),'phase_tb.sv'],'vlog')
  log=run(a.questa_bin/'vsim.exe',['-c','work.source249_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'vsim');assert 'PASS PHASE251' in log
  result=dict(passed=True,frames=71,directed_replays=2,persistent_bytes_checked=73*332,receipt_bytes_checked=72*754,base_bytes_checked=73*4398,guards=4);print(json.dumps(result))
 result.update(rtl_hashes=hashes,input_hashes=pins,scope=__doc__,packet_binding=False,CDC=False,full_arm=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
