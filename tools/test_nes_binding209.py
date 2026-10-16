# SPDX-License-Identifier: MIT
"""Bounded replay of208 actual C packets/65816 ACKs through selected207 queue.
Queue schedules are deliberately regrouped to four credits, not recorded208
SPI status timing. Top mux assignments are extracted verbatim; peer outputs
are modeled for truth-table checks. No whole-board/FPS/physical claim.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_board204 import ROOT,BASE,sha
from replay_nes_window184 import TAIL

def crc(data,bits,poly,start):
 c=start
 for b in data:
  c^=b<<(bits-8)
  for _ in range(8):c=((c<<1)^ (poly if c&(1<<(bits-1)) else 0))&((1<<bits)-1)
 return c

def events(folder):
 rows=[];sent=done=0;ack=bytes(12);pending=[];full=0
 def spi(tx,rx):rows.append(f'T {len(tx)} {tx.hex()} {rx.hex()}')
 def status():
  b=bytes([0,0xf7,(1 if sent!=done else 0)|(2 if done else 0)|(4 if sent-done==4 else 0),sent>>8,sent&255,done>>8,done&255])+ack
  spi(bytes([0xe0])+bytes(19),b+bytes([crc(b[1:],8,7,0)]))
 def drain():
  nonlocal done,ack
  for packet,a in pending:
   rows.append(f'A {len(packet)} {packet.hex()} {a.hex()}');done+=1;ack=a;status()
  pending.clear()
 status()
 for i,p in enumerate(sorted(folder.glob('req-*.bin')),1):
  b=p.read_bytes();a=(folder/f'ack-{i:04}.bin').read_bytes()
  assert a[1]==b[0] and a[2:10]==b[2:10] and a[10:]==b'\x65\x9a'
  if b[0] in (1,3):drain()
  tx=b'\xe1'+b;tx+=crc(tx,16,0x1021,65535).to_bytes(2,'big');spi(tx,bytes(len(tx)));sent+=1;pending.append((b,a));status()
  if len(pending)==4:full+=1;drain()
  elif b[0] in (1,3):drain()
 drain();assert sent==done and full>0
 rows.append('E 0 0 0');return '\n'.join(rows)+'\n',dict(packets=sent,full_windows=full,events=len(rows)-1)

MUX=r'''
`timescale 1ns/1ps
module mux209;
 reg core_reset=0,sink_oe204=1,bus_oe_n=1,sink_dir204=0,bus_dir=0,status_receive=0;
 reg [7:0] sink_data204=8'ha6,bus_data=8'h5c;
 wire consumer_oe,consumer_dir;wire [7:0] consumer_data;
 wire SNES_DATABUS_DIR,SNES_DATABUS_OE;wire [7:0] SNES_DATA;
 reg boot_selected=0,observer_selected=0,status_selected=0,sink_selected=0;
 reg boot_miso=0,observer_miso=0,status_miso=0,sink_miso=0;wire SPI_MISO;
 // EXTRACTED_TOP_ASSIGNMENTS
 integer v,count,checks=0;
 reg expected_oe,expected_dir;reg [7:0] expected_data;
 initial begin
  for(v=0;v<64;v++)begin
   {core_reset,status_receive,sink_oe204,bus_oe_n,sink_dir204,bus_dir}=v;#1;
   expected_oe=(core_reset||(sink_oe204==bus_oe_n))&&!status_receive;
   expected_dir=!core_reset&&(sink_oe204!=bus_oe_n)&&(sink_oe204?bus_dir:sink_dir204);
   expected_data=sink_oe204?bus_data:sink_data204;
   if(SNES_DATABUS_OE!==expected_oe||SNES_DATABUS_DIR!==expected_dir)$fatal(1,"mux control %d",v);
   if(SNES_DATA!==(expected_dir&&!expected_oe?expected_data:8'hzz))$fatal(1,"mux data %d",v);checks++;
  end
  for(v=0;v<256;v++)begin
   {boot_selected,observer_selected,status_selected,sink_selected,boot_miso,observer_miso,status_miso,sink_miso}=v;#1;
   count=integer'(boot_selected)+integer'(observer_selected)+integer'(status_selected)+integer'(sink_selected);
   if(count!=1)begin if(SPI_MISO!==1'bz)$fatal(1,"MISO collision %d",v);end
   else if(SPI_MISO!==(boot_selected?boot_miso:observer_selected?observer_miso:status_selected?status_miso:sink_miso))$fatal(1,"MISO owner %d",v);
   checks++;
  end
  $display("PASS BIND209 TOPMUX checks=%0d",checks);
 end
endmodule
'''

def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 board=BASE/'probes/nes-board207/source02';old=BASE/'probes/nes-window184-coupled/evidence/route02';pins={}
 prep=json.loads((board/'preparation207.json').read_bytes())
 names=['nes_domain_reset124.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv','sink-program.hex']
 for n in names:
  assert sha(board/n)==prep['sources'][n];pins[n]=sha(board/n);shutil.copyfile(board/n,a.out/n)
  if n!='sink-program.hex':assert sha(board/n)==sha(old/n),n
 top=(board/'fxpak_nes_screen137_top.sv').read_text();pins['fxpak_nes_screen137_top.sv']=sha(board/'fxpak_nes_screen137_top.sv')
 names2=['consumer_oe','consumer_dir','consumer_data','SNES_DATABUS_DIR','SNES_DATABUS_OE','SNES_DATA','SPI_MISO']
 assigns=[]
 for n in names2:
  found=re.findall(r'assign\s+'+n+r'\s*=.*?;',top,re.S);assert len(found)==1,n;assigns+=found
 (a.out/'mux209.sv').write_text(MUX.replace('// EXTRACTED_TOP_ASSIGNMENTS','\n'.join(assigns)),encoding='utf8',newline='\n')
 head=(ROOT/'tests/nes-functional/sink_window184_tb.sv').read_text().split(' initial begin',1)[0].replace('module sink_window184_tb;','module coupled_tb;')
 # Read decode of the actual sink must leave new descriptor/aperture and save SRAM unowned.
 decode='''
  for(integer a=24'h6040;a<=24'h6050;a++)begin address=a;rn=0;wn=1;#100;if(!oe||dir)$fatal(1,"descriptor sink collision");checks++;end
  for(integer a=24'h400800;a<=24'h400fff;a++)begin address=a;rn=0;wn=1;#100;if(!oe||dir)$fatal(1,"aperture sink collision");checks++;end
  address=24'h700000;#100;if(!oe||dir)$fatal(1,"save SRAM sink collision");checks++;release_read;
 '''
 tail=TAIL.replace('input_fd=$fopen',decode+'\n  input_fd=$fopen')
 tail=tail.replace('PASS WINDOW184 COUPLED','PASS BIND209 QUEUE')
 (a.out/'coupled_tb.sv').write_text(head+tail,encoding='utf8',newline='\n')
 def run(cmd,label):
  with (a.out/(label+'.log')).open('wb') as f:q=subprocess.run(list(map(str,cmd)),cwd=a.out,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:];return s
 run([a.questa_bin/'vlib.exe','work'],'vlib')
 run([a.questa_bin/'vlog.exe','-sv',*names[:-1],'coupled_tb.sv','mux209.sv'],'vlog')
 cases=[]
 for mode in ['normal','partial']:
  folder=BASE/'probes/nes-join208/test08'/mode;data,case=events(folder)
  (a.out/'events.txt').write_text(data,encoding='ascii');(a.out/(mode+'-events.txt')).write_text(data,encoding='ascii')
  s=run([a.questa_bin/'vsim.exe','-c','work.coupled_tb','work.mux209','-do','onerror {quit -code 1}; run -all; quit -f'],mode)
  m=re.search(r'PASS BIND209 QUEUE events=(\d+) packets=(\d+) checks=(\d+) fault=(\d+)',s);assert m and int(m[1])==case['events'] and int(m[2])==case['packets'] and int(m[4])==0,s[-2000:]
  assert 'PASS BIND209 TOPMUX checks=320' in s
  case.update(mode=mode,checks=int(m[3]),input_pins={f.name:sha(f) for f in sorted(folder.glob('*.bin')) if f.name.startswith(('req-','ack-'))},events_sha256=sha(a.out/(mode+'-events.txt')));cases.append(case)
  print(json.dumps({k:v for k,v in case.items() if k!='input_pins'}),flush=True)
 r=dict(passed=True,cases=cases,board_pins=pins,queue_unchanged_since184=True,top_mux_verbatim=True,mux_truth_table_checks=320,scope=__doc__,physical=False,full_board=False,new_fit=False,new_package=False,public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_binding209.py','tools/replay_nes_window184.py','tests/nes-functional/sink_window184_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
