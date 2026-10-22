# SPDX-License-Identifier: MIT
"""Unchanged actual ARM264 packets, integrated265 RTL, independent C oracle.

Internal controls are observed from the immutable received queue (oracle only).
The SNES bus reads display context once after seal; general execution is native
C plus bus allocations, not a target65816 run or a physical display measurement.
"""
from pathlib import Path
import argparse,json,os,shutil
from nes_delta231 import BASE,ROOT,sha,once
from nes_joint265 import sources
from probe_nes_joint264 import prepare as prior_prepare,tb as prior_tb,run


def tb():
 s=prior_tb().replace('joint264_tb','joint265_tb').replace('nes_joint264 dut','nes_joint265 dut')
 s=once(s,'integer n,ignore263,events263,copy263;', 'integer n,ignore263,events263,copy263,head265;')
 s=once(s,' begin\n  n=dut.flow.qlen;', ' begin\n  head265=dut.flow.queue.retired;n=dut.flow.qlen;')
 s=once(s,'  wait(dut.flow.qdone);@(negedge host_clk);\n  wait(dut.flow.state==dut.flow.IDLE);', '  wait(dut.flow.queue.retired!=head265);')
 s=once(s,' reg enable=0;', ''' integer internal265=0,display_reads265=0;
 reg [7:0] expected_display265[0:23];
 // Passive reference observer: only received immutable RAM, no RTL writes.
 always @(negedge host_clk)begin : observe265
  integer n,ignore265;reg [7:0] op,b;
  if(active263&&dut.flow.state==dut.flow.OSETUP)begin
   op=dut.flow.header[0];
   if(op==15||op==10||op==11||op==3)begin
    n=dut.flow.qlen;
    for(integer i=0;i<n;i++)begin
     b=dut.flow.queue.buffer[{dut.flow.queue.retired[1:0],8'd0}+i];
     ignore265=call263(1,i,b);
     if(op==15&&i>=16&&i<40)expected_display265[i-16]=b;
    end
    ignore265=call263(2,n,0);internal265++;
    $fwrite(events261,"internal,%0d,%0d,%0d\\n",f,op,n);
   end
  end
 end
 reg enable=0;''')
 a=s.index('  if(p263[0]==3)begin\n   wait(v_sealed);');b=s.index('  ordinary263++;',a)
 checks=s[a:b];checks=checks.replace('  if(p263[0]==3)begin\n   wait(v_sealed);',' task check_final265;begin').rstrip()+' endtask\n'
 s=s[:a]+s[b:];s=once(s,' task tiles_task263;', checks+' task tiles_task263;')
 s=once(s,"    token261(dut.flow.last_map_token);wr261(24'h006058,8'h5a);", '''    check_final265();
    // Exactly one bounded display-context read, independent of manifest ACK.
    for(integer j=0;j<24;j++)begin
     rd261(24'h006070+j,val263);
     if(val263!==expected_display265[j])$fatal(1,"display context265 frame%0d byte%0d",f,j);
     display_reads265++;
    end
    token261(dut.flow.last_map_token);wr261(24'h006058,8'h5a);''')
 s=once(s,'if(dut.flow.ordinary_ready)ordinary_task263();', '''if(dut.flow.ordinary_ready)begin
    if(dut.flow.header[0]==15||dut.flow.header[0]==10||dut.flow.header[0]==11||dut.flow.header[0]==3)$fatal(1,"manifest exposed to SNES265");
    ordinary_task263();
   end''')
 s=once(s,'if(dut.flow.qdone&&dut.flow.header[0]!=1)', 'if(dut.flow.state==dut.flow.OSETUP)')
 s=s.replace('PASS JOINT264','PASS JOINT265')
 return s


def prepare(d,last):
 src,pins,stats=prior_prepare(d,last);src.pop('nes_joint264.sv')
 for n,s in sources().items():(d/n).write_text(s,encoding='utf-8',newline='\n');src[n]=''
 (d/'joint265_tb.sv').write_text(tb(),encoding='utf-8',newline='\n')
 for name in ['nes_joint265.py','probe_nes_joint265.py']:
  path=ROOT/'tools'/name;shutil.copyfile(path,d/name);pins[path.relative_to(BASE).as_posix()]=sha(path)
 return src,pins,stats


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--last',type=int,default=975);a=p.parse_args()
 d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src,pins,stats=prepare(d,a.last)
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer264.c','-o','producer263.dll'],d,'native')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint265_tb.sv'],d,'vlog')
 log=run(a.questa_bin/'vsim.exe',['-c','-sv_lib','producer263','work.joint265_tb',f'+LAST={a.last}','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',1800)
 assert f'PASS JOINT265 frames={a.last-904}' in log
 r=dict(passed=True,frames=a.last-904,rtl_hashes={n:sha(d/n) for n in src},input_hashes=pins,scope=__doc__,actual_SNES=False,full_ARM=False,physical=False,whole_FIT=False)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(log[-1500:])


if __name__=='__main__':main()
