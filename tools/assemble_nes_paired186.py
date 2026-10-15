# SPDX-License-Identifier: MIT
"""Update routed184's4096B SNES ROM only; preserve all RTL, placement and timing."""
from pathlib import Path
import argparse,json,shutil,re
from nes_game147 import ROOT,sha
from nes_spi_boot import run
from nes_cf68_pair_preflight import encode,decode
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','client','work','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert a.work.as_posix().isascii() and not a.work.exists()
 assert sha(a.baseline/'nes_sink_spi165.sv')==sha(ROOT.parent/'probes/nes-window184-coupled/evidence/route02/nes_sink_spi165.sv')
 pins={f.relative_to(a.baseline).as_posix():sha(f) for f in a.baseline.rglob('*') if f.is_file()}
 prep=json.loads((a.baseline/'preparation.json').read_bytes())
 for n,h in prep['sources'].items():assert sha(a.baseline/n)==h,n
 shutil.copytree(a.baseline,a.work)
 mif,=a.work.glob('db/board.ram*_nes_sink_bus165_*.hdl.mif');s=mif.read_text();assert 'WIDTH=8;' in s and 'DEPTH=4096;' in s
 def image(t):
  rows=re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',t,re.M);assert len(rows)==4096
  d={int(k):int(v,2) for k,v in rows};return bytes(d[i] for i in range(4096))
 assert image(s)==bytes.fromhex((a.work/'sink-program.hex').read_text())
 new=bytes.fromhex((a.client/'sink-program.hex').read_text());assert len(new)==4096 and new!=image(s)
 s=re.sub(r'^(\s*)(\d+)(\s*:\s*)([01]{8})(;)',lambda m:m[1]+m[2]+m[3]+f'{new[int(m[2])]:08b}'+m[5],s,flags=re.M)
 assert image(s)==new;mif.write_text(s,encoding='utf8',newline='\n');shutil.copyfile(a.client/'sink-program.hex',a.work/'sink-program.hex')
 for label,args in [('mif186',['quartus_cdb.exe','board','--update_mif']),('asm186',['quartus_asm.exe','board']),('cpf186',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  log=run([a.quartus_bin/args[0],*args[1:]],a.work,label,300);assert 'successful' in log and '0 errors' in log,log[-2000:]
 preserved={}
 for n,h in pins.items():
  assert sha(a.baseline/n)==h,n
  if n.endswith(('.v','.sv','.vhd','.qsf','.qpf','.sdc','.fit.rpt','.fit.summary','.sta.rpt','.sta.summary','.rcf','.pin')):
   assert sha(a.work/n)==h,n;preserved[n]=h
 assert image(mif.read_text())==new
 raw=(a.work/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 (a.work/'fpga_n186.bi3').write_bytes(packed)
 result=dict(passed=True,baseline_pins=pins,unchanged_routing_and_sources=preserved,method='generated ROM MIF update + Quartus CDB/ASM/CPF, no MAP/FIT/STA',client_sha256=sha(a.work/'sink-program.hex'),rbf_sha256=sha(a.work/'output_files/board.rbf'),fpga_sha256=sha(a.work/'fpga_n186.bi3'),mif_sha256=sha(mif),public_sources={'tools/assemble_nes_paired186.py':sha(ROOT/'tools/assemble_nes_paired186.py')},physical=False)
 (a.work/'result186.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS186 ROM update and routing preservation',len(preserved))
if __name__=='__main__':main()
