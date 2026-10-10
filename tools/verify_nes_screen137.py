# SPDX-License-Identifier: MIT
"""Read-only137 evidence integrity and the exact scope of reused functional evidence."""
from pathlib import Path
import argparse,csv,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 meta=json.loads((ROOT/'analysis/screen137-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 def read(n):return json.loads((e/n).read_bytes())
 hw=read('hardware136-parsed02/result.json');assert hw['physical_run136_passed'] and len(hw['progress'])==47
 assert hw['progress'][-1]['elapsed_ms']=='491600' and hw['user_confirmed']['menu_return'] and hw['user_confirmed']['restoration']
 test=read('test01/result137.json');assert test['passed'] and sum(f['pixels'] for f in test['frames'])==184320
 counter=read('counter01/result.json');assert counter['passed'] and counter['one_step_cases']==26112 and counter['wrong_increment_rejected']
 assert counter['candidate_sha256']==sha(e/'fit03/nes_rom_loader.sv') and counter['reference_sha256']==sha(e/'test01/nes_rom_loader.sv')
 names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(e/'fit03/board.qsf').read_text())
 # The full141ms core simulation predates the counter factor. Every other
 # compiled source matches, with the counter change checked independently.
 different=[n for n in names if sha(e/'fit03'/n)!=sha(e/'test01'/n)]
 assert different==['nes_rom_loader.sv'],different
 for n in ['board.qsf','board.sdc','screen-program.hex']:
  assert sha(e/'fit01'/n)==sha(e/'fit03'/n),n
 bus=read('bus01/result.json');assert bus['passed'] and bus['rom_bytes']==65536
 assert bus['boundary_sha256']==sha(e/'fit03/nes_screen_bus137.sv')
 assert bus['rom_sha256']==sha(e/'fit03/client/screen137.sfc')
 normal=read('client06/result.json');assert normal['passed'] and normal['model']==[3,6024,0]
 assert normal['inputs']['rom']==sha(e/'fit03/client/screen137.sfc')
 actual=b''.join((e/f'test01/packet-{i}.bin').read_bytes() for i in range(1,4))
 assert hashlib.sha256(actual).hexdigest()==normal['inputs']['packets']
 for directory,model in [('client07',[0,0,2]),('client08',[0,2008,7])]:
  m=read(directory+'/result.json');assert m['passed'] and m['model']==model
 # Audit actual DMA destinations as well as pixels; rejected packets must
 # never update the PPU. Only the header-negative consumes a WRAM packet.
 startup=[[1,24,1,32768,16384]]
 frame=[[0,128,64,32768,2008],[1,24,126,16404,1920],[1,24,126,18324,60],[2,34,126,18384,8]]
 for directory,wanted in [('client06',startup+frame*3),('client07',startup),('client08',startup+frame[:1])]:
  rows=(e/directory/'trace.tsv').read_text().splitlines()
  dmas=[list(map(int,s.split()[1:6])) for s in rows if s.startswith('DMA\t')]
  assert dmas==wanted,(directory,dmas)
 timing=list(csv.DictReader((e/'fit03/timing134.tsv').read_text().splitlines(),delimiter='\t'))
 for kind in ['setup','hold']:
  rows=[r for r in timing if r['group']=='same_clock' and r['type']==kind]
  assert len(rows)==12 and all(float(r['slack'])>0 for r in rows)
 assert meta['hardware_screen_tested'] is False and meta['new_sd_package'] is False
 print(json.dumps(dict(passed=True,files=len(files),physical_run136=True,rtl_pixels=184320,
   snes_display_pixels=183552,counter_cases=26112,same_clock_pass=True,hardware_screen_tested=False)))
if __name__=='__main__':main()
