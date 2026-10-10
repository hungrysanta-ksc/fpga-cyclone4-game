# SPDX-License-Identifier: MIT
"""Causal control: bypass the late guard in a test-only ROM; timing must fail."""
from pathlib import Path
import argparse,json,subprocess,sys
from nes_spi_boot import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['client','packets','chr-hex','mesen','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir();rom=a.out/'rom';rom.mkdir()
 data=(a.client/'screen146.sfc').read_bytes()
 needle=bytes.fromhex('af05407e8de01fad1242300f');assert data.count(needle)==1
 changed=needle[:-2]+bytes([0x80,0x0f]);bad=data.replace(needle,changed)
 assert sum(x!=y for x,y in zip(data,bad))==1
 (rom/'screen146.sfc').write_bytes(bad)
 cmd=[sys.executable,'-B',str(ROOT/'tools/test_nes_screen146_client.py'),'--client',str(rom),'--mode','late','--out',str(a.out/'run')]
 for n in ['packets','chr-hex','mesen']:cmd+=['--'+n,str(getattr(a,n.replace('-','_')))]
 run=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (a.out/'negative.log').write_bytes(run.stdout)
 assert run.returncode!=0 and b'assert shown[3]==black[3]+1' in run.stdout,run.stdout[-2000:]
 model=list(map(int,(a.out/'run/model.tsv').read_text().split()));assert model==[30,60240,0]
 (a.out/'result.json').write_text(json.dumps(dict(passed=True,guard_bypass_rejected=True,full_run=model,original_rom_sha256=sha(a.client/'screen146.sfc'),mutated_rom_sha256=sha(rom/'screen146.sfc')),indent=2)+'\n')
 print('PASS146 guard-bypass negative rejected at delayed reveal assertion')
if __name__=='__main__':main()
