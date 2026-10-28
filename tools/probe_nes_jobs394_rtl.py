# SPDX-License-Identifier: MIT
"""Physical SPI2slot host + retained independent checker on twelve frames.
Source bytes are recorded fixtures;no live ARM/ROM schedule claim."""
import argparse,json,re,shutil,struct
from pathlib import Path
from probe_nes_jobs394_native import fixtures,current_view
from probe_nes_refill267 import run
from nes_delta231 import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--rtl',required=True,type=Path);p.add_argument('--arm',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--guards',action='store_true');a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 sources=['nes_mux260.sv','nes_queue260.sv','nes_spi270.sv','nes_validator278.sv','nes_tile_link394.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv','nes_bulk_aperture188.sv']
 for n in sources:shutil.copyfile(a.rtl/n,d/n)
 shutil.copyfile(ROOT/'tests/nes-jobs394/record_tb.sv',d/'record_tb.sv')
 def save(name,values,width=2):(d/name).write_text('\n'.join(f'{v:0{width}x}'for v in values)+'\n',newline='\n')
 for f in range(905,917):
  wire=[bytes.fromhex(x)for x in json.loads((a.arm/f'wire{f}.json').read_text())];jobs=fixtures(f,a.arm)
  save(f'packet{f}.hex',b''.join(wire));save(f'sizes{f}.hex',[len(wire)]+[len(x)for x in wire],4)
  data=bytearray();desc=bytearray();lens=[];tiles=bytearray();info=[]
  for j in jobs:
   r=bytes.fromhex(j['record']);b=bytes.fromhex(j['data']);data+=b;lens.append(len(b));desc+=r+struct.pack('<HHB',j['offset'],len(b),int(j['first'])+2*int(j['last']))
   if r[9]<2:
    assert j['first']and j['last'];tiles+=b;info.append(r[9]+(int.from_bytes(r[10:12],'little')<<2)+(len(b)//(32 if r[9]else 16)<<12))
  save(f'data{f}.hex',data);save(f'desc{f}.hex',desc);save(f'length{f}.hex',[len(lens)]+lens,4);save(f'tile{f}.hex',tiles);save(f'tileinfo{f}.hex',[len(info)]+info,6);save(f'view{f}.hex',current_view(f))
 q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*sources,'record_tb.sv'],d,'vlog')
 out=run(q/'vsim.exe',['-c','record_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',240);m=re.search(r'PASS RECORD394 frames=(\d+) bytes=(\d+) actual_reads=(\d+) max_credit=(\d+)',out);assert m
 negative=[]
 if a.guards:
  from guard_nes_jobs394 import guards
  negative=guards(d,q,run)
 (d/'result.json').write_text(json.dumps(dict(passed=True,frames=int(m[1]),source_bytes=int(m[2]),actual_read_events=int(m[3]),max_credit=int(m[4]),guards=negative,RTL={n:sha(d/n)for n in sources},test=sha(d/'record_tb.sv'),scope=__doc__),indent=2)+'\n');print(m[0])
if __name__=='__main__':main()
