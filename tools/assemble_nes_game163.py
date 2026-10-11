# SPDX-License-Identifier: MIT
"""Update only the routed162 program ROM using Quartus update_mif + assembler."""
from pathlib import Path
import argparse,json,shutil,re,hashlib
from nes_spi_boot import run,sha
from nes_cf68_pair_preflight import encode,decode
def main():
 p=argparse.ArgumentParser()
 for n in ['work','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();w=a.work;m=json.loads((w/'preparation163.json').read_bytes())
 assert set(m['changed'])=={'game-program.hex'} and m['ids']==['6B','E5']
 for n,h in m['copied'].items():assert sha(w/n)==m['changed'].get(n,h),n
 before=sha(w/'output_files/board.rbf')
 # Inferred $readmemh ROM is compiled into this generated MIF. Updating the
 # source HEX alone is ineffective; prove old MIF matches162 before replacing.
 mif,=w.glob('db/board.ram*_nes_game_bus151_*.hdl.mif')
 text=mif.read_text();assert 'WIDTH=8;' in text and 'DEPTH=2048;' in text
 rows=re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',text,re.M)
 assert len(rows)==2048 and {int(i) for i,v in rows}==set(range(2048))
 old=bytes(dict((int(i),int(v,2)) for i,v in rows)[i] for i in range(2048))
 old_text=''.join(f'{v:02x}\n' for v in old)
 assert m['copied']['game-program.hex'] in [hashlib.sha256(old_text.encode()).hexdigest(),hashlib.sha256(old_text.replace('\n','\r\n').encode()).hexdigest()]
 new=bytes(int(v,16) for v in (w/'game-program.hex').read_text().split());assert len(new)==2048
 text=re.sub(r'^(\s*)(\d+)(\s*:\s*)([01]{8})(;)',lambda x:x[1]+x[2]+x[3]+f'{new[int(x[2])]:08b}'+x[5],text,flags=re.M)
 mif.write_text(text,encoding='utf8',newline='\n')
 assert bytes(dict((int(i),int(v,2)) for i,v in re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',text,re.M))[i] for i in range(2048))==new
 for label,args in [('mif163',['quartus_cdb.exe','board','--update_mif']),('asm163',['quartus_asm.exe','board']),('cpf163',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  log=run([a.quartus_bin/args[0],*args[1:]],w,label,300)
  assert 'successful' in log and '0 errors' in log,log[-2000:]
 preserved={}
 for n,h in m['copied'].items():
  if n.endswith(('.sv','.v','.vhd','.qsf','.qpf','.sdc','.fit.rpt','.fit.summary','.sta.rpt','.sta.summary','.rcf')):
   assert sha(w/n)==h,n;preserved[n]=h
 raw=(w/'output_files/board.rbf').read_bytes();assert sha(w/'output_files/board.rbf')!=before
 packed=encode(raw);assert decode(packed)==raw;(w/'fpga_n163.bi3').write_bytes(packed)
 result=dict(candidate='NES-GAME-163',passed=True,method='verified generated program-ROM MIF replacement, quartus_cdb --update_mif then ASM/CPF; no MAP/FIT/STA',generated_mif=mif.relative_to(w).as_posix(),mif_sha256=sha(mif),rtl_ids=['6B','E5'],client='163',program_sha256=sha(w/'game-program.hex'),rbf_bytes=len(raw),rbf_sha256=sha(w/'output_files/board.rbf'),packed_bytes=len(packed),packed_sha256=sha(w/'fpga_n163.bi3'),unchanged_routing_and_sources=preserved,new_map_fit=False,physical=False)
 (w/'result163.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copy2(__file__,w/'executed-assemble163.py');print('PASS163 RAM update/ASM',len(raw),len(packed),len(preserved))
if __name__=='__main__':main()
