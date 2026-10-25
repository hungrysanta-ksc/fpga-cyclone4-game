# SPDX-License-Identifier: MIT
"""Incremental actual ARM packets -> TB SPI queue -> real sequential cache/ROM.

The EA admission/CDC/lease is NOT implemented by this fixture. Timing is a
bounded necessary-gate experiment, not a full frame or physical ARM WCET.
"""
import argparse,json,re,shutil
from pathlib import Path
from nes_delta231 import BASE,sha
from nes_cache360 import apply
from probe_nes_cache359 import TB as previous
from probe_nes_refill267 import run
from probe_nes_irq267 import IRQ
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--arm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 arm=json.loads((a.arm/'result.json').read_text());warm=arm['rows'][2];assert arm['passed']
 irq=IRQ();irqrow=irq.call('SysTick_Handler');irqcycles=irqrow['instructions']+24
 packets=b''.join(bytes.fromhex(p['hex']) for p in warm['packets']);assert len(packets) in (24,52) and warm['source_decode_delta']==0
 (d/'packet.hex').write_text(''.join(f'{b:02x}\n' for b in packets),newline='\n')
 tb=previous.replace('cache359_tb','cache360_tb').replace('COST359','COST360').replace('CACHE359','CACHE360')
 tb=tb.replace('parameter integer PHASE=5677152;', 'parameter integer PHASE=5677152,CPI=1;')
 tb=tb.replace('reg [7:0] packet[0:47];',f'reg [7:0] packet[0:{len(packets)-1}];reg [15:0] hints[0:4];integer tag_ready=0,packet_base=0;')
 start=tb.index('  // Actual ARM firstpacket delay');end=tb.index('  filled=$realtime;',start)
 producer=f'   #{1458201.190476+warm["source_decode_delta"]/84*1000};\n   #(CPI*{warm["reset_instructions"]}/0.084);\n'
 charged=False
 for c in warm['calls']:
  producer+=f'   #(CPI*{c["instructions"]}/0.084);\n'
  if not c['packet_bytes']:continue
  n=c['packet_bytes']
  if not charged:producer+=f'   #(CPI*{irqrow["instructions"]}/0.084+24/0.084);\n';charged=True
  producer+=f'''   ss=0;
   for(integer j=packet_base;j<packet_base+{n};j++)for(integer k=7;k>=0;k--)begin mosi=packet[j][k];#190.476190476;sck=1;#190.476190476;sck=0;end
   ss=1;#8000;wire_end=$realtime;
   for(integer k=0;k<packet[packet_base+1];k++)hints[tag_ready+k]={{packet[packet_base+13+2*k],packet[packet_base+12+2*k]}};
   tag_ready=tag_ready+packet[packet_base+1];packet_base=packet_base+{n};
   $display("PACKET360 CPI=%0d tags=%0d ready_ns=%0f",CPI,tag_ready,$realtime-started);
'''
 tb=tb[:start]+'''  fork
  begin : transmit
'''+producer+'''  end
  begin : consume
   for(integer j=0;j<5;j++)begin wait(tag_ready>j);for(integer k=0;k<16;k++)get(22'h200000+hints[j]*16+k);end
  end
  join
'''+tb[end:]
 tb=tb.replace('reads!=272','reads!=80').replace('j<17','j<5').replace("({packet[13+2*j],packet[12+2*j]}*16)",'hints[j]*16').replace("({packet[13],packet[12]}*16)",'hints[0]*16')
 tb=tb.replace('realtime started,wire_end,filled;', 'realtime started,wire_end,filled,hit_started;').replace('before_reads=reads;\n  for(integer j=0;j<5;', 'before_reads=reads;hit_started=$realtime;\n  for(integer j=0;j<5;')
 tb=tb.replace('  $display("COST360', '  $display("HIT360 CPI=%0d elapsed_ns=%0f",CPI,$realtime-hit_started);\n  $display("COST360')
 tb=tb.replace('COST360 phase=%0d SPI=', 'COST360 phase=%0d CPI=%0d SPI=').replace('PHASE,spi_bytes,reads','PHASE,CPI,spi_bytes,reads')
 (d/'cache360_tb.sv').write_text(tb,newline='\n');pins={str(a.arm/'result.json'):sha(a.arm/'result.json'),str(irq.path):sha(irq.path)}
 names=['nes_chr_cache192.sv','nes_native_arbiter165.sv','nes_rom_physical.sv']
 for n in names:
  p=BASE/'probes/nes-raster355/fixed01'/n;shutil.copyfile(p,d/n);pins[str(p)]=sha(p)
 apply(d);q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*names,'cache360_tb.sv'],d,'vlog');rows=[]
 for phase,cpi in ((5677152,1),(7368026,1),(5677152,2)):
  raw=run(q/'vsim.exe',['-c','work.cache360_tb',f'-gPHASE={phase}',f'-gCPI={cpi}','-do','onerror {quit -code 1};run -all;quit -f'],d,f'phase{phase}-cpi{cpi}',240)
  assert 'PASS CACHE360' in raw
  m=re.search(r'COST360 phase=(\d+) CPI=(\d+) SPI=(\d+) ROM=(\d+) core=(\d+) wire_ns=([\d.]+) fill_ns=([\d.]+)',raw);assert m
  rows.append(dict(zip(('phase','CPI','SPI_bytes','ROM_bytes','core_reads','wire_ns','fill_ns'),map(float,m.groups()))))
  rows[-1]['cache_hit_replay_ns']=float(re.search(r'HIT360 CPI=\d+ elapsed_ns=([\d.]+)',raw)[1])
 for n in [*names,'cache360_tb.sv','packet.hex']:pins[str(d/n)]=sha(d/n)
 result=dict(passed=True,rows=rows,IRQ=irqrow,exception_entry_exit_cycle_allocation=24,pins=pins,scope=__doc__,integrated_EA=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
