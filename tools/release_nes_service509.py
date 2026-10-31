# SPDX-License-Identifier: MIT
"""Label-only MMC509 trial build and pinned507 image conversion; no new FIT."""
import argparse,json,struct,subprocess,zlib
from pathlib import Path
from nes_schedule492 import funcs,sha
from nes_cf68_pair_preflight import encode,decode
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def prepare(a):
 assert sha(a.baseline/'obj-nes-100/firmware.stm')=='70b41341c3a5987b433e0aaa5403f6988a006d271e1af4484236f9e71611875d'
 a.out.mkdir(parents=True,exist_ok=False);d=a.out/'patch';d.mkdir()
 for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
  s=(a.baseline/n).read_text();assert '502'in s
  (d/n).write_text(s.replace('502','509'),encoding='utf8',newline='\n')
 write(a.out/'result.json',dict(passed=True,scope='Equal-length labels only',files={p.name:sha(p)for p in d.iterdir()}))
def assemble(a):
 known=read(ROOT/'analysis/fault507-verification.json')['FPGA'];archive=read(a.archive)
 for n,h in known['source_inputs'].items():assert sha(a.board/n)==h,n
 for p in (a.board/'output_files').iterdir():
  if p.suffix in ['.sof','.rpt','.summary']:
   n='board01/'+p.relative_to(a.board).as_posix();assert sha(p)==archive[n]['SHA256'],n
 assert 'Successful'in(a.board/'output_files/board.fit.summary').read_text()
 a.out.mkdir(parents=True,exist_ok=False);rbf=a.out/'board.rbf'
 with (a.out/'cpf.log').open('wb')as f:
  subprocess.run([str(a.quartus/'quartus_cpf.exe'),'-c',str(a.board/'output_files/board.sof'),str(rbf)],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
 raw=rbf.read_bytes();packed=encode(raw);assert decode(packed)==raw
 image=a.out/'fpga_mmc509.bi3';image.write_bytes(packed)
 write(a.out/'result.json',dict(passed=True,source_inputs=known['source_inputs'],SOF_SHA256=sha(a.board/'output_files/board.sof'),RBF_SHA256=sha(rbf),BI3_SHA256=sha(image),BI3_bytes=len(packed),matching507_FIT_STA_reused=True,new_FIT=False,physical=False))
def verify(a):
 old,new=funcs(a.baseline/'obj-nes-100/sd2snes.elf'),funcs(a.arm/'obj-nes-100/sd2snes.elf');assert old==new and len(new)>700
 before=(a.baseline/'obj-nes-100/firmware.stm').read_bytes();fw=a.arm/'obj-nes-100/firmware.stm';after=fw.read_bytes()
 # genhdr without -v hashes the build timestamp into bytes4..7. It is not
 # an executable change; independently validate length/body CRC below.
 assert len(before)==len(after)==212956 and before[:4]==after[:4]==b'STM3'
 assert before[32:].replace(b'502',b'509')==after[32:]
 size,crc,inverse=struct.unpack_from('<III',after,8);header=len(after)-size
 assert header==512 and zlib.crc32(after[header:])==crc and crc^inverse==0xffffffff
 assert after[20:header]==b'\xff'*(header-20)
 changed=[]
 for p in a.baseline.rglob('*'):
  rel=p.relative_to(a.baseline)
  if not p.is_file()or any(x.startswith(('obj-','.dep-'))for x in rel.parts):continue
  q=a.arm/rel;assert q.is_file(),str(rel)
  if sha(p)!=sha(q):changed.append(rel.as_posix());assert p.read_bytes().replace(b'502',b'509')==q.read_bytes(),str(rel)
 assert set(changed)=={'nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION','.ARG_VERSION'}
 v=read(ROOT/'analysis/service509-verification.json');assembly=read(a.assembly/'result.json');programmer=read(a.programmer/'result.json')
 assert v['functional_passed']and assembly['passed']and programmer['passed']
 assert programmer['image_sha256']==assembly['BI3_SHA256']and programmer['rbf_sha256']==assembly['RBF_SHA256']
 prod=ROOT.parent/'probes/nes-repeat227/arm01/src/fpga.c';mark='struct nes_diag_input {FIL file;'
 assert (a.arm/'fpga.c').read_text().split(mark,1)[1]==prod.read_text().split(mark,1)[1]
 assert sha(ROOT.parent/'probes/nes-capture502/ARM01/src/obj-nes-100/firmware.stm')=='d079ea1a891ef05765a46afbc83d8f7e01b3010edd33da0822e38aced13e10fd'
 assert sha(ROOT.parent/'probes/nes-output489/client04/sink165.sfc')=='d550b69b15c535b56b5ad022cf009e0a17b27a7bd12d12da890e37f31aa3e7a6'
 write(a.out,dict(passed=True,candidate='MMC509',limited_functional_trial_ready=True,hardware_verified=False,physical_FPS=None,firmware_SHA256=sha(fw),firmware_B=len(after),Flash_free_B=36,linked_functions_equal=len(new),all_functions_equal_to509_ARM01=True,nonheader_bytes_label_only=True,changed_sources=changed,assembly=assembly,programmer=programmer,limits=['Boot-core ROM trace is not matched gameplay timing','Physical startup,first-level performance and menu return require user test','Full reset/CDC/IO and IRQ stack signoff unchanged']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','assemble','verify'])
 for n in ['baseline','arm','board','archive','quartus','assembly','programmer','out']:p.add_argument('--'+n,type=Path)
 a=p.parse_args();globals()[a.mode](a)
