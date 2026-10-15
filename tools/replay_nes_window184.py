# SPDX-License-Identifier: MIT
"""Replay actual C SPI transactions and actual65816 packet/ACK events in RTL."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
TAIL=r'''
 integer input_fd,result_fd,got,size,kind,events_count=0,packet_count=0;
 reg [2071:0] first_word,second_word;
 reg [7:0] expected_byte;
 initial begin
  trace_on=0;#100;reset=0;#200;
  input_fd=$fopen("events.txt","r");if(!input_fd)$fatal(1,"input missing");
  while(!$feof(input_fd))begin
   got=$fscanf(input_fd,"%s %d %h %h\n",kind,size,first_word,second_word);
   if(got!=4)$fatal(1,"event parse %d",got);
   if(kind=="E")begin
    $display("PASS WINDOW184 COUPLED events=%0d packets=%0d checks=%0d fault=%0d",events_count,packet_count,checks,fault);
    $fclose(input_fd);$finish;
   end else if(kind=="T")begin
    if(size<1||size>259)$fatal(1,"SPI size");
    for(i=0;i<size;i++)tx[i]=first_word[(size-1-i)*8+:8];
    transfer(size);
    for(i=0;i<size;i++)begin
     expected_byte=second_word[(size-1-i)*8+:8];
     if(rx[i]!==expected_byte)$fatal(1,"event %d SPI byte %d got%h expected%h",events_count,i,rx[i],expected_byte);
     checks++;
    end
   end else if(kind=="A")begin
    if(size<16||size>256||!dut.ready)$fatal(1,"head missing");
    read_byte(24'h006004,size&255);read_byte(24'h006005,size>>8);release_read;
    for(i=0;i<size;i++)read_byte(24'h400000+i,first_word[(size-1-i)*8+:8]);release_read;
    if(second_word[88+:8]==8'he4)begin stop=1;#300;read_byte(24'h006001,8'h80);release_read;end
    for(i=0;i<12;i++)write_byte(24'h006010+i,second_word[(11-i)*8+:8]);
    write_byte(24'h00601c,8'ha5);#500;packet_count++;
   end else $fatal(1,"event kind");
   events_count++;
  end
  $fatal(1,"missing end");
 end
 initial begin #1000000000;$fatal(1,"watchdog");end
endmodule
'''
def main():
 p=argparse.ArgumentParser()
 for n in ['coupled','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--rtl-dir',type=Path)
 p.add_argument('--modes',nargs='+',default=['normal','stop_copy','stop_long'])
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 baseline=a.rtl_dir or ROOT.parent/'probes/nes-window184/evidence/test03';pins={}
 for n in ['nes_domain_reset124.sv','nes_sink_queue184.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv','sink-program.hex']:
  shutil.copyfile(baseline/n,a.out/n);pins[n]=sha(baseline/n)
 if a.rtl_dir:
  from nes_window184_compact import compact
  assert (baseline/'nes_sink_queue184.sv').read_text()==compact((ROOT/'src/nes/diagnostic/nes_sink_queue184.sv').read_text())
 else:assert pins['nes_sink_queue184.sv']==sha(ROOT/'src/nes/diagnostic/nes_sink_queue184.sv')
 head=(ROOT/'tests/nes-functional/sink_window184_tb.sv').read_text().split(' initial begin',1)[0]
 (a.out/'coupled_tb.sv').write_text(head.replace('module sink_window184_tb;','module coupled_tb;')+TAIL,encoding='utf8')
 def run(cmd,name):
  with (a.out/(name+'.log')).open('wb') as f:q=subprocess.run([str(x) for x in cmd],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
  s=(a.out/(name+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-2500:];return s
 run([a.questa_bin/'vlib.exe','work'],'vlib')
 run([a.questa_bin/'vlog.exe','-sv','nes_domain_reset124.sv','nes_sink_queue184.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv','coupled_tb.sv'],'vlog')
 cases=[]
 for mode in a.modes:
  src=a.coupled/mode/'events.txt';shutil.copyfile(src,a.out/'events.txt')
  s=run([a.questa_bin/'vsim.exe','-c','work.coupled_tb','-do','onerror {quit -code 1}; run -all; quit -f'],mode)
  m=re.search(r'PASS WINDOW184 COUPLED events=(\d+) packets=(\d+) checks=(\d+) fault=(\d+)',s);assert m,s[-2000:]
  assert int(m[4])==(mode not in ['normal','reference','inherit'])
  cases.append(dict(mode=mode,events=int(m[1]),packets=int(m[2]),checks=int(m[3]),fault=int(m[4]),events_sha256=sha(src)))
  print(json.dumps(cases[-1]),flush=True)
 result=dict(passed=True,cases=cases,inputs=pins,coupled_result_sha256=sha(a.coupled/'result.json'),public_sources={n:sha(ROOT/n) for n in ['tools/replay_nes_window184.py','tests/nes-functional/sink_window184_tb.sv']},scope='Actual C/65816 event order replay through actual RTL/SNES bus. File scheduling is not cycle-accurate concurrent CPU/MCU execution or FPS.',physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
