# SPDX-License-Identifier: MIT
"""Actual ARM262 H2/BEGIN bytes -> SPI queue -> CDC -> core context/BEGIN.

BEGIN reads/checks/ACK are a bus service model, not an actual CPU. Other non-map
stream/H2 digest/manifest producers remain261 fixtures. Map service uses the
900-clock sensitivity from261's actual cold CPU; this is not a warm WCET.
"""
import argparse,json,os,re,shutil
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha,once
from nes_joint262 import sources
from probe_nes_joint261 import tb as prior_tb,prepare as prior_prepare,run,packets

EXTRA=r'''
 reg [7:0] prelude262[0:75],begin262[0:27];integer context_bytes262=0,begins262=0;
 always @(posedge clk)if(!reset)begin
  if(dut.context_valid&&context_ready)context_bytes262++;
  if(dut.v_begin_valid)begin
   if(!dut.core.encoder.context_complete||!dut.flow.prelude_done)$fatal(1,"BEGIN before context retirement");
   begins262++;
  end
 end
 task send262(input integer offset262,input integer length262);
 reg [15:0] crc262;
 begin
  tx[0]=8'he1;crc262=c16(16'hffff,8'he1);
  for(integer i=0;i<length262;i++)begin tx[i+1]=prelude262[offset262+i];crc262=c16(crc262,tx[i+1]);end
  tx[length262+1]=crc262[15:8];tx[length262+2]=crc262[7:0];transfer(length262+3);
 end endtask
 task prelude_task262;
 reg [7:0] b262;integer before262;
 begin
  name=$sformatf("prelude%0d.hex",f);$readmemh(name,prelude262);before262=context_bytes262;
  if(PRENEG==1)begin prelude262[50]=0;send262(48,28);wait(1'b0);end
  if(PRENEG==2)begin prelude262[12]=31;send262(0,47);wait(1'b0);end
  if(PRENEG==4)prelude262[19]=prelude262[19]^1;
  if(PRENEG==6)prelude262[47]=prelude262[47]^1;
  send262(0,48);
  if(PRENEG==3)begin
   wait(dut.flow.prelude_done);prelude262[2]=1;send262(0,48);wait(1'b0);
  end
  send262(48,28);
  wait(dut.flow.ordinary_ready);
  if(context_bytes262-before262!=32)$fatal(1,"context ingress count");
  for(integer i=0;i<28;i++)begin
   rd261(24'h400000+i,b262);begin262[i]=b262;
   if(b262!==prelude262[48+i])$fatal(1,"BEGIN packet read");
  end
  // Consumer validates the full pinned BEGIN before issuing its existing ACK.
  // General BEGIN semantics and actual65816 execution remain outside this run.
  wr261(24'h006010,0);wr261(24'h006011,1);
  for(integer i=2;i<10;i++)wr261(24'h006010+i,begin262[i]);
  wr261(24'h00601a,8'h65);wr261(24'h00601b,8'h9a);wr261(24'h00601c,8'ha5);
  wait(dut.flow.begun&&dut.flow.state==dut.flow.IDLE&&v_ready);
  packet_seq261=2;
  $fwrite(events261,"prelude_done,%0d,%0t,32\n",f,$time);
 end endtask
 initial begin : abort_prelude262
  if(PRENEG==5)begin wait(dut.context_valid);@(negedge clk);test_abort=1;end
 end
 initial begin : negative_prelude262
 reg [7:0] frozen262[0:1023];
 if(PRENEG)begin
  wait(source_fault);repeat(4)@(negedge clk);
  if(v_sealed||lease_valid||staged||rack||flow_retired)$fatal(1,"prelude completion after fault");
  for(integer i=0;i<1024;i++)frozen262[i]=dut.core.memory[i];
  repeat(256)@(negedge clk);
  for(integer i=0;i<1024;i++)if(frozen262[i]!==dut.core.memory[i])$fatal(1,"prelude RAM after STOP");
  $display("PASS JOINT262 PRENEG=%0d context=%0d begins=%0d",PRENEG,context_bytes262,begins262);$finish;
 end
 end
'''


def tb():
 s=prior_tb().replace('joint261_tb','joint262_tb').replace('nes_joint261 dut','nes_joint262 dut')
 s=once(s,'RPC=0,NEG=0,WINDOW=4','RPC=0,NEG=0,WINDOW=4,PRENEG=0')
 for port in ['.context_valid(context_valid),','.context_data(context_data),','.v_begin_valid(v_begin_valid),','.v_target_bank(v_target_bank),','.v_raw_count(v_raw_count),']:
  s=once(s,port,'')
 s=once(s,' task output_frame;',EXTRA+'\n task output_frame;')
 start=s.index('  for(j=0;j<32;j++)begin\n   wait(context_ready)');end=s.index('  while(op!=5)',start)
 s=s[:start]+'  prelude_task262();\n'+s[end:]
 s=once(s,'   if(op==2&&c[32])', '   if(op==1)continue;\n   if(op==2&&c[32])')
 s=s.replace('&&!NEG)', '&&!NEG&&!PRENEG)')
 s=once(s,'if(!RPC&&!NEG&&!PRENEG)begin','if(!RPC&&!NEG&&(PRENEG==0||PRENEG==6))begin')
 s=once(s,'    #23280;', '    #41904; // 900 master clocks allocation, replaces261 setup500')
 s=s.replace('PASS JOINT261','PASS JOINT262')
 return s


def prepare(d,last,single=False,shared=True):
 src,pins,stats=prior_prepare(d,last,single)
 src.pop('nes_joint261.sv');new=sources(shared)
 for n,s in new.items():(d/n).write_text(s,encoding='utf-8',newline='\n');src[n]=''
 for f in range(905,last+1):
  path=BASE/f'probes/nes-joint262/arm01/frame{f}.packets';pins[path.relative_to(BASE).as_posix()]=sha(path)
  pp=packets(path);assert [p[0] for p in pp[:2]]==[13,1]
  (d/f'prelude{f}.hex').write_text(b''.join(pp[:2]).hex(' '),encoding='utf-8')
  # Map values/splits are unchanged; bind the current ARM file, not only260.
  old=[p for p in packets(BASE/f'probes/nes-batch260/arm01/frame{f}.packets') if p[0]==14]
  fresh=[p for p in pp if p[0]==14];assert len(old)==len(fresh)
  for a,b in zip(old,fresh):assert a[:2]+a[4:]==b[:2]+b[4:]
  if not single:(d/f'map{f}.hex').write_text(b''.join(fresh).hex(' '),encoding='utf-8')
 (d/'joint262_tb.sv').write_text(tb(),encoding='utf-8',newline='\n')
 for n in ['nes_joint262.py','probe_nes_joint262.py']:
  path=ROOT/'tools'/n;pins[path.relative_to(BASE).as_posix()]=sha(path);shutil.copyfile(path,d/n)
 return src,pins,stats


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--last',type=int,default=975);p.add_argument('--guards',action='store_true');p.add_argument('--separate-prelude',action='store_true');a=p.parse_args()
 d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src,pins,stats=prepare(d,a.last,shared=not a.separate_prelude)
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint262_tb.sv'],d,'vlog')
 log=run(a.questa_bin/'vsim.exe',['-c','work.joint262_tb',f'+LAST={a.last}','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim')
 assert f'PASS JOINT262 frames={a.last-904}' in log
 flat={}
 for line in (d/'blocks.txt').read_text().splitlines():
  frame,tok,n,b=line.split();flat.setdefault(int(frame),bytearray()).extend(bytes.fromhex(b))
 for frame,b in flat.items():
  old=BASE/'probes/nes-joint249/blocktest03';size=int((old/f'frame{frame}.meta').read_text().split()[0]);assert b==bytes.fromhex((old/f'frame{frame}.expected.hex').read_text())[:size]
 guards=[]
 if a.guards:
  for kind in ['NEG','PRENEG']:
   for case in range(1,7):
    gd=d/f'{kind.lower()}{case:02}';gd.mkdir()
    for fixture in d.iterdir():
     if fixture.suffix in ['.hex','.palette','.expected','.lens']:shutil.copyfile(fixture,gd/fixture.name)
    run(a.questa_bin/'vmap.exe',['-c'],gd,'vmap0');run(a.questa_bin/'vmap.exe',['work',str(d/'work')],gd,'vmap')
    log=run(a.questa_bin/'vsim.exe',['-c','work.joint262_tb',f'-g{kind}={case}','+LAST=905','-do','onerror {quit -code 1};run -all;quit -f'],gd,'vsim')
    assert f'PASS JOINT262 {kind}={case}' in log;guards.append([kind,case])
 r=dict(passed=True,shared_prelude_mailbox=not a.separate_prelude,guards=guards,frames=len(flat),source_bytes=sum(map(len,flat.values())),map_frames=stats,rtl_hashes={n:sha(d/n) for n in src},input_hashes=pins,scope=__doc__,full_ARM=False,actual_SNES=False,physical=False,whole_FIT=False)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(log[-1700:])


if __name__=='__main__':main()
