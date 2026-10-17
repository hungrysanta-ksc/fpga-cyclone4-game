# SPDX-License-Identifier: MIT
"""Remove CHECK enable's redundant fault gate under the proven state invariant."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha,replace
def transform(s):
 return replace(s,' nes_rom_boot boot(.check_enable(check_enable && !spi_fault)', ''' // 219: reset and every control transition maintain fault -> !check_enable.
 // The read_reset fault cancellation and exported RUN gates remain intact.
 nes_rom_boot boot(.check_enable(check_enable)''')
def prepare(out):
 old=BASE/'probes/nes-retire219/source01';p=json.loads((old/'preparation219.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n
  (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 before=(old/'nes_spi_boot.sv').read_text();after=transform(before)
 (out/'nes_spi_boot.sv').write_text(after,encoding='utf8',newline='\n')
 (out/'enable.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in p['sources']},baseline=p['baseline'],changed=['nes_rom_loader.sv','nes_rom_spi.sv','nes_spi_boot.sv'],
  public_sources=p['public_sources']|{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},no_package=True,adopted=False)
 assert sorted(n for n,h in r['sources'].items() if h!=r['baseline'][n])==r['changed']
 (out/'preparation219.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(changed=r['changed'],files=len(r['sources']))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
