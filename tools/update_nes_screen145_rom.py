# SPDX-License-Identifier: MIT
"""Update only M9K contents on selected routing; no repeated placement."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
from nes_spi_boot import sha
def main():
 p=argparse.ArgumentParser()
 for n in ['fit','client','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();shutil.copytree(a.fit,a.out)
 pins={x.relative_to(a.fit).as_posix():sha(x) for x in a.fit.rglob('*') if x.is_file()}
 for n in ['screen-program.hex','screen145.sfc','result.json']:
  shutil.copy2(a.client/n,a.out/'client'/n)
 shutil.copy2(a.client/'screen-program.hex',a.out/'screen-program.hex')
 # Quartus caches $readmemh contents in its generated MIF. Replacing the
 # source HEX alone leaves that MIF stale, even when --update_mif succeeds.
 mif_files=list((a.out/'db').glob('board.ram*_nes_screen_bus137_*.hdl.mif'))
 assert len(mif_files)==1,mif_files
 mif=mif_files[0];old_mif=mif.read_text()
 assert 'WIDTH=8;' in old_mif and 'DEPTH=24576;' in old_mif
 def decode(text):
  rows=re.findall(r'(\d+)\s*:\s*([01]{8});',text)
  values={int(x):int(y,2) for x,y in rows}
  assert len(rows)==len(values)==24576 and set(values)==set(range(24576))
  return bytes(values[i] for i in range(24576))
 assert decode(old_mif)==bytes.fromhex((a.fit/'screen-program.hex').read_text())
 new_bytes=bytes.fromhex((a.client/'screen-program.hex').read_text())
 assert len(new_bytes)==24576
 header=old_mif.split('CONTENT BEGIN')[0]
 mif.write_text(header+'CONTENT BEGIN\n'+''.join(f'\t{i} :\t{v:08b};\n' for i,v in enumerate(new_bytes))+'END;\n',newline='\n')
 assert decode(mif.read_text())==new_bytes
 with (a.out/'update-mif145.log').open('wb') as f:r=subprocess.run([str(a.quartus_bin/'quartus_cdb.exe'),'board','--update_mif'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 assert r.returncode==0
 assert decode(mif.read_text())==new_bytes
 for n,h in pins.items():
  assert sha(a.fit/n)==h,n
  if n.endswith(('.sv','.v','.vhd','.qsf','.sdc','.qpf','.fit.rpt','.fit.summary','.sta.rpt','.sta.summary')):assert sha(a.out/n)==h,n
 result=dict(passed=True,new_map_fit=False,generated_mif=mif.relative_to(a.out).as_posix(),generated_mif_sha256=sha(mif),mif_all_bytes_verified=len(new_bytes),program_sha256=sha(a.out/'screen-program.hex'),client_sha256=sha(a.out/'client/screen145.sfc'),inputs=pins,scope='Source HEX and generated MIF contents updated and byte-verified; fitted routing/timing/RTL preserved. New program tested separately.')
 (a.out/'rom-update145.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS145 ROM-only MIF update; routing preserved')
if __name__=='__main__':main()
