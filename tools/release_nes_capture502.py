# SPDX-License-Identifier: MIT
"""Isolated502 hardware trial: fitted capture overlay, unchanged493 executable functions."""
import argparse,csv,json,struct,zlib
from pathlib import Path
from nes_schedule492 import funcs,sha
from nes_cf68_pair_preflight import encode,decode
ROOT=Path(__file__).resolve().parents[1]

def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,r):p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')

def prepare(a):
 known=read(ROOT/'analysis/boot493-verification.json')
 assert sha(a.arm/'obj-nes-100/firmware.stm')==known['ARM']['firmware_SHA256']
 a.out.mkdir(parents=True,exist_ok=False);d=a.out/'patch';d.mkdir();before={}
 for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
  p=a.arm/n;s=p.read_text();assert '493'in s;before[n]=sha(p)
  (d/n).write_text(s.replace('493','502'),encoding='utf8',newline='\n')
 write(a.out/'preparation.json',dict(baseline_firmware_SHA256=known['ARM']['firmware_SHA256'],baseline_sources=before,patch_sources={p.name:sha(p)for p in d.iterdir()},scope='Only equal-length marker/ROM/FPGA/log/version strings change'))

def assemble(a):
 proof=read(ROOT/'analysis/capture502-verification.json');pins=read(a.board/'source-pins.json')
 assert proof['bounded_capture_consumer_gate_passed'] and pins['board_inputs']==proof['FPGA']['whole_board_inputs']
 for n,h in pins['board_inputs'].items():assert sha(a.board/n)==h,n
 for n,h in proof['FPGA']['report_SHA256'].items():
  p=a.board/n if n.endswith('.tsv')else a.board/'output_files'/n
  assert sha(p)==h,n
 archive=read(a.archive)
 sof=a.board/'output_files/board.sof'
 assert sha(sof)==archive['board01/output_files/board.sof']['SHA256']
 for view in ['implementation','nominal']:
  rows=list(csv.DictReader((a.board/(view+'-paths204.tsv')).open(),delimiter='\t'))
  assert rows and all(float(x['slack'])>=0 for x in rows if((x['from_clock']=='nes')==(x['to_clock']=='nes')))
 raw=(a.board/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 a.out.mkdir(parents=True,exist_ok=False);image=a.out/'fpga_mmc502.bi3';image.write_bytes(packed)
 write(a.out/'result.json',dict(passed=True,source_inputs=pins['board_inputs'],SOF_SHA256=sha(sof),RBF_SHA256=sha(a.board/'output_files/board.rbf'),BI3_SHA256=sha(image),BI3_bytes=len(packed),matching502_FIT_STA_reused=True,new_FIT_or_Questa=False,physical=False))

def verify(a):
 known=read(ROOT/'analysis/boot493-verification.json');capture=read(ROOT/'analysis/capture502-verification.json');assembly=read(a.assembly/'result.json');programmer=read(a.programmer/'result.json')
 assert sha(a.baseline/'obj-nes-100/firmware.stm')==known['ARM']['firmware_SHA256']
 old,new=funcs(a.baseline/'obj-nes-100/sd2snes.elf'),funcs(a.arm/'obj-nes-100/sd2snes.elf')
 assert old==new and len(new)>700
 before=(a.baseline/'obj-nes-100/firmware.stm').read_bytes();fw=a.arm/'obj-nes-100/firmware.stm';after=fw.read_bytes()
 assert before[:4]==after[:4]==b'STM3' and before[32:].replace(b'493',b'502')==after[32:]
 assert len(after)==len(before)==212844
 size,crc,inverse=struct.unpack_from('<III',after,8);header=len(after)-size
 assert header==512 and zlib.crc32(after[header:])==crc and (crc^inverse)==0xffffffff
 assert after[20:header]==b'\xff'*(header-20)
 changed=[]
 for p in a.baseline.rglob('*'):
  rel=p.relative_to(a.baseline)
  if not p.is_file()or any(x.startswith(('obj-','.dep-'))for x in rel.parts):continue
  q=a.arm/rel;assert q.is_file(),str(rel)
  if sha(p)!=sha(q):changed.append(rel.as_posix())
 assert set(changed)=={'nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION','.ARG_VERSION'},changed
 assert (a.baseline/'.ARG_VERSION').read_bytes().replace(b'493',b'502')==(a.arm/'.ARG_VERSION').read_bytes()
 text=(a.arm/'nes_menu_diagnostic.c').read_text()+(a.arm/'nes_checkpoint112.c').read_text()
 labels=['NES MMC3 502.nh1','mmc502.nes','fpga_mmc502.bi3','nes-progress-mmc502.txt','nes-budget-mmc502.txt','nes-game-last-mmc502.txt']
 assert all(x in text for x in labels) and '493'not in text
 assert assembly['passed']and programmer['passed']
 assert assembly['source_inputs']==capture['FPGA']['whole_board_inputs']
 assert programmer['image_sha256']==assembly['BI3_SHA256'] and programmer['rbf_sha256']==assembly['RBF_SHA256']
 # The actual deployed programmer suffix must match the tested227 implementation.
 prod=ROOT.parent/'probes/nes-repeat227/arm01/src/fpga.c';mark='struct nes_diag_input {FIL file;'
 assert (a.arm/'fpga.c').read_text().split(mark,1)[1]==prod.read_text().split(mark,1)[1]
 assert sha(a.client/'sink165.sfc')==read(ROOT/'analysis/output489-verification.json')['SNES']['client_SHA256']
 r=dict(passed=True,candidate='MMC502',limited_functional_trial_ready=True,public_release=False,hardware_verified=False,physical_FPS=None,
  implementation='analysis/capture502-verification.json',physical_baseline='MMC493',client_ABI='4891',profile_hex='7b',status_version=3,labels=labels,
  ARM=dict(firmware_SHA256=sha(fw),firmware_B=len(after),linked_functions_equal=len(new),all_function_addresses_sizes_bytes_equal_to493=True,all_nonheader_bytes_label_only=True,changed_sources=[n for n in changed if n!='.ARG_VERSION'],generated_version_cache_label_only=True,Flash_free_B=148,new_global_RAM_B=0,RUN_workspace_B=31848,new_measurement_overhead=False),
  FPGA=capture['FPGA'],assembly=assembly,programmer=programmer,SNES_SHA256=sha(a.client/'sink165.sfc'),
  protected='Independent checks/STOP/finalACK/VBlank/base/menu/GBC/save executable paths unchanged;collector guards are in capture502 proof',
  limits=['New hardware load/menu/FPS not yet tested','Programmer/FatFS uses modeled GPIO/DONE;not physical programming','Capture/consumer proof is bounded;actual shared ARM/SPI/IRQ/ROM effects require returned logs','Full reset/CDC/IO and IRQ stack signoff unchanged'],
  next='Matched493/502 gameplay;save three distinct logs per run and verify capture errors,final-display intervals,STOP/menu before A2 budget')
 write(a.out,r);print(json.dumps(dict(passed=True,functions=len(new),Flash_free_B=148,hardware_verified=False)))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','assemble','verify'])
 for n in ['arm','baseline','board','archive','assembly','programmer','client','out']:p.add_argument('--'+n,type=Path)
 a=p.parse_args();{'prepare':prepare,'assemble':assemble,'verify':verify}[a.mode](a)
