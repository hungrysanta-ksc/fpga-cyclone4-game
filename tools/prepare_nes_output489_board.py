# SPDX-License-Identifier: MIT
"""489 payload sampling removes late command qualification, not write admission."""
import argparse,json,shutil,hashlib
from pathlib import Path
from check_nes_game478 import sha
ROOT=Path(__file__).resolve().parents[1]
def loader_transform(s):
 old='  else if(payload_accept)begin\n   load_address'
 assert s.count(old)==1
 return s.replace(old,'''  //489 Speculative RECEIVE sampling is unobservable until accepted SETUP.
  // The unchanged phase/fault/command logic remains the write authority.
  // Never sample in SETUP/WRITE/HOLD: an accepted pulse must drain unchanged.
  else if(phase[RECEIVE] && load_valid)begin
   load_address''')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['baseline','client','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 old=json.loads((ROOT/'analysis/supply485-verification.json').read_text())['whole_board_inputs']
 for n,h in old.items():
  assert sha(a.baseline/n)==h,n;f=a.out/n;f.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.baseline/n,f)
 f=a.out/'nes_rom_loader.sv';f.write_text(loader_transform(f.read_text()),encoding='utf8',newline='\n')
 f=a.out/'nes_sink_bus165.sv';s=f.read_text()
 for before,after in [('program_rom[0:4095]','program_rom[0:5119]'),("15'h0fc0","15'h13c0"),('program_rom[address_sync[11:0]]',"program_rom[address_sync[12:0] & {1'b1,{2{!address_sync[14]}},10'h3ff}]")]:
  assert s.count(before)==1;s=s.replace(before,after)
 f.write_text(s,encoding='utf8',newline='\n');program=bytes.fromhex((a.client/'sink-program.hex').read_text());assert len(program)==5120
 shutil.copyfile(a.client/'sink-program.hex',a.out/'sink-program.hex');pins={n:sha(a.out/n)for n in old}
 r={'baseline_inputs':old,'board_inputs':pins,'changed':[n for n in old if old[n]!=pins[n]],'client_SHA256':sha(a.client/'sink165.sfc'),'program_SHA256':hashlib.sha256(program).hexdigest(),'scope':__doc__}
 assert set(r['changed'])=={'nes_rom_loader.sv','nes_sink_bus165.sv','sink-program.hex'}
 (a.out/'source-pins.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({'changed':r['changed']}))
