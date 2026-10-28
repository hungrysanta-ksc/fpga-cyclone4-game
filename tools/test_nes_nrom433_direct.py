# SPDX-License-Identifier: MIT
"""Actual 227 E9 decoder, lease, tile source and SNES bus with 433 plan."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from nes_delta231 import ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--serializer',required=True,type=Path);p.add_argument('--tile',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
s=json.loads((a.serializer/'result.json').read_text());t=json.loads((a.tile/'result.json').read_text());assert s['passed'] and t['passed'] and s['batch_sha256']==sha(a.serializer/'batch.bin') and t['rom_sha256']==sha(a.rom) and s['plan_sha256']==t['plan_sha256']
names=['nes_direct206.sv','nes_source_epoch207.sv','nes_capture_lease201.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_tile205.sv','nes_plan_spi200.sv','nes_plan_batch206.sv','nes_tile_bulk206.sv','nes_bulk_control194.sv','nes_bulk_aperture188.sv','nes_native_arbiter165.sv','nes_rom_physical.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv']
for n in names:shutil.copyfile(a.board/n,d/n)
shutil.copyfile(ROOT/'tests/nes-nrom433/direct_tb.sv',d/'direct_tb.sv');s=(ROOT/'tests/nes-functional/spi200_bus.svh').read_text();s=s.replace('SPI_HALF=62.5,SPI_SETUP=200,SPI_HOLD=200,SPI_GAP=2000','SPI_HALF=190.476190476,SPI_SETUP=2000,SPI_HOLD=2000,SPI_GAP=4000');(d/'spi200_bus.svh').write_text(s)
(d/'frame.mem').write_text(''.join(f'{x:02x}\n' for x in a.rom.read_bytes()[16400:16560]));shutil.copyfile(a.tile/'frame.expected',d/'frame.expected');(d/'batch.hex').write_text(''.join(f'{x:02x}\n' for x in (a.serializer/'batch.bin').read_bytes()))
exe=Path('C:/altera_standard/25.1std/questa_fse/win64')
for name,cmd in [('vlib',['vlib','work']),('vlog',['vlog','-sv',*names,'direct_tb.sv']),('simulation',['vsim','-L','altera_mf_ver','-c','work.nrom433_tb','-do','onerror {quit -code 1};run -all;quit -f'])]:
 with(d/(name+'.log')).open('wb') as f:q=subprocess.run([str(exe/(cmd[0]+'.exe')),*cmd[1:]],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-4000:]
log=(d/'simulation.log').read_text(errors='replace');assert 'PASS NROM433' in log and 'Errors: 0' in log,log[-4000:]
result={'passed':True,'rom_sha256':sha(a.rom),'batch_sha256':sha(a.serializer/'batch.bin'),'tile_output_sha256':sha(a.tile/'frame.expected'),'direct_sha256':sha(a.board/'nes_direct206.sv'),'scope':'actual 227 E9 SPI/decoder/tile aperture/lease RTL; C serialized plans replayed, ROM and capture lease modeled, manual SNES bus/retire, not live 65816 or whole board'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
