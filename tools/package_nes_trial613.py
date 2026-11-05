"""Deliver the actual 608 ROM + 612 board + identically relabeled ARM610."""
import argparse,hashlib,json,zipfile
from collections import Counter
from pathlib import Path
from check_nes_wire600 import ROOT,read,sha
from nes_cf68_pair_preflight import encode,decode
from budget_nes_board611 import fit,timing
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('arm','board','reference','client','checks','romcheck','image','programmer','prior','out','report'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();old=read(ROOT/'analysis/trial577-package.json');ev=read(ROOT/'analysis/oe612-verification.json')
 pins=read(a.board/'inputs613.json')
 for n,h in pins.items():assert sha(a.board/n)==h
 assert [n for n in pins if pins[n]!=ev['inputs'][n]]==['sink-program.hex']
 client=sha(a.client/'sink165.sfc');assert client==ev['client_SHA']
 rom=(a.client/'sink165.sfc').read_bytes();assert bytes.fromhex((a.board/'sink-program.hex').read_text())==rom[:5056]+rom[-64:]
 romcheck=read(a.romcheck/'result.json');assert romcheck['program']==pins['sink-program.hex'] and romcheck['client']==client
 assert romcheck['log']==sha(a.romcheck/'vsim.log') and romcheck['bytes']==5120
 sta=timing(a.board,'paths612.tsv');assert all(float(v['slack'])>=0 for v in sta['worst'].values())
 assert Counter((a.board/'paths612.tsv').read_text().splitlines())==Counter((a.reference/'paths612.tsv').read_text().splitlines())
 cost=fit(a.board);assert all(cost[k]==ev['fit'][k] for k in ('LE','comb','FF','RAM_bits','M9K'))
 armcheck=read(a.checks/'result.json');fw=(a.arm/'obj-nes-100/firmware.stm').read_bytes()
 assert sha(a.arm/'obj-nes-100/firmware.stm')==armcheck['firmware'] and armcheck['identical_functions']==792
 assert [(x['start_s'],x['end_s']) for x in armcheck['checks']['windows']['accepted']]==[(5,40),(40,55)]
 prog=read(a.programmer/'result.json');assert prog['passed']
 raw=(a.image/'board.rbf').read_bytes();bi3=(a.image/'fpga_mmc613.bi3').read_bytes()
 assert encode(raw)==bi3 and decode(bi3)==raw
 assert prog['image_sha256']==sha(a.image/'fpga_mmc613.bi3') and prog['rbf_sha256']==sha(a.image/'board.rbf')
 marker='NES MMC3 613.nh1';rompath='sd2snes/nes/mmc613.nes';logs=[f'sd2snes/nes-{n}-mmc613.txt' for n in ('progress','budget','game-last')]
 for path in [marker,'sd2snes/fpga_mmc613.bi3',rompath,*logs]:assert (path if path==marker else '/'+path).encode()+b'\0' in fw
 prefix='01-MMC613-SD-ROOT/';files={prefix+'sd2snes/firmware.stm':fw,prefix+'sd2snes/fpga_mmc613.bi3':bi3,prefix+marker:b'',
  prefix+'sd2snes/nes/ROM-NOT-INCLUDED.txt':b'Copy your unchanged mmc577.nes to mmc613.nes. CRC32 5a04eed7.\n',
  'README-KO.txt':(ROOT/'docs/nes-mmc613-trial.ko.md').read_bytes()}
 assert sha(a.prior)==old['ZIP_SHA256']
 with zipfile.ZipFile(a.prior) as z:
  for n in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin'):
   data=z.read('01-MMC577-SD-ROOT/'+n);assert hashlib.sha256(data).hexdigest()==old['files']['01-MMC577-SD-ROOT/'+n]
   files[prefix+n]=data
 assert not any('RESTORE' in n or n.lower().endswith(('.nes','.sav','.srm','.rtc')) for n in files)
 result=dict(candidate='MMC613',gate='limited physical trial only',physical_verified=False,firmware_SHA256=armcheck['firmware'],
  SOF_SHA256=sha(a.board/'output_files/board.sof'),RBF_SHA256=sha(a.image/'board.rbf'),BI3_SHA256=sha(a.image/'fpga_mmc613.bi3'),
  client_SHA256=client,changed_board_inputs=['sink-program.hex'],inputs=pins,board=cost,STA=sta,STA_paths_identical_to612=True,
  ARM=armcheck,ROM_read=romcheck,programmer=prog,logs=logs,required_ROM={**old['required_ROM'],'path':rompath},
  ROM_included=False,RESTORE_included=False,scope='New whole ARM link and FPGA FIT/STA with actual 608 ROM. Same instructions and 612 circuit timing; prior two-phase schedule retained. Not hardware FPS or physical menu test.',
  files={n:hashlib.sha256(data).hexdigest() for n,data in files.items()})
 files['manifest.json']=(json.dumps(result,indent=2)+'\n').encode()
 a.out.mkdir(parents=True,exist_ok=False);archive=a.out/'MMC613-TRIAL.zip'
 with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
  for n,data in files.items():z.writestr(n,data)
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None and set(z.namelist())==set(files)
  for n,data in files.items():assert z.read(n)==data
 result.update(ZIP_SHA256=sha(archive),ZIP_bytes=archive.stat().st_size)
 a.report.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(archive,result['ZIP_SHA256'])
