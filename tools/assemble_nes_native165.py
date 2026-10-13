# SPDX-License-Identifier: MIT
"""Assemble the already routed boundary165/map02; never run MAP/FIT or edit it."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha
from nes_spi_boot import run
from nes_cf68_pair_preflight import encode,decode
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','work','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert a.work.as_posix().isascii() and not a.work.exists()
 manifest=a.baseline/'evidence-manifest.json'
 assert sha(manifest)=='f2b144a23be65efbe440519e968e155eea374f821a683b23c7eeb161a96ab2a2'
 pins=json.loads(manifest.read_bytes());src=a.baseline/'map02'
 old={n[6:]:h for n,h in pins.items() if n.startswith('map02/')}
 assert old and set(old)=={f.relative_to(src).as_posix() for f in src.rglob('*') if f.is_file()}
 for n,h in old.items():assert sha(src/n)==h,n
 result=json.loads((src/'result.json').read_bytes());assert result['fit_pass'] and result['same_clock_pass']
 shutil.copytree(src,a.work)
 for label,args in [('asm165',['quartus_asm.exe','board']),('cpf165',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  log=run([a.quartus_bin/args[0],*args[1:]],a.work,label,300)
  assert 'successful' in log and '0 errors' in log,log[-2000:]
 preserved={}
 for n,h in old.items():
  if n.endswith(('.v','.sv','.vhd','.hex','.qsf','.qpf','.sdc','.fit.rpt','.fit.summary','.map.rpt','.map.summary','.pin')):
   assert sha(a.work/n)==h,n;preserved[n]=h
 # Source evidence is immutable, including Quartus databases and reports.
 for n,h in old.items():assert sha(src/n)==h,n
 raw=(a.work/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 (a.work/'fpga_n165.bi3').write_bytes(packed)
 r=dict(passed=True,baseline_manifest_sha256=sha(manifest),source_pins=old,preserved=preserved,selected='boundary165/map02',new_map_fit=False,rbf_bytes=len(raw),rbf_sha256=sha(a.work/'output_files/board.rbf'),packed_bytes=len(packed),packed_sha256=sha(a.work/'fpga_n165.bi3'),client_sha256=sha(a.work/'sink-program.hex'),public_sources={'tools/assemble_nes_native165.py':sha(Path(__file__))},scope='Quartus ASM/CPF of selected routed database. Original source/database unchanged; conditional IO/reset limits retained. Not a new timing closure or physical test.')
 (a.work/'assembly165.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['source_pins','preserved']}))
if __name__=='__main__':main()
