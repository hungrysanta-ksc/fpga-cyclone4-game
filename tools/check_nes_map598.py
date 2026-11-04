"""Bind a summary-sidecar diagnostic to the selected MMC577 compact collector."""
import argparse
import binascii
import json
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

from check_nes_game478 import encode, sha
from check_nes_region595 import Q, ROOT

CORE = 'nes_native_compact181'
TAP = 'nes_map_seal598.sv'


def checked_board(board):
    manifest=json.loads((ROOT/'analysis/whole580-manifest.json').read_bytes())['FPGA_inputs']
    names=(CORE+'.sv','nes_native_frame201.sv','nes_native_raster181.sv','nes_live_joint.sv',
           'nes_native_export203.sv','nes_native_mailbox165.sv','nes_native_spi165.sv','nes_patch_capture181.sv')
    for name in names:
        assert sha(board/name)==manifest[name]['sha256'], name


def collector(board, tap):
    s=(board/(CORE+'.sv')).read_text()
    port=' output reg active,owned,valid,'
    assert s.count(port)==1
    s=s.replace(port,''' input wire read_summary,input wire [4:0] read_group,output wire summary_hit,
 output wire [63:0] summary,output wire [15:0] map_crc,
'''+port)
    tail=''' nes_map_seal598 tap(.clk(clk),.clear(reset || release_scene || starting),.copy(copy_busy),
  .owned_valid(owned && valid),.read_summary(read_summary),.write_group(group_count[4:0]-5'd1),
  .read_group(read_group),.column(copy_column),.groups(group_count),.cell_word(previous_value),
  .summary_hit(summary_hit),.summary(summary),.map_crc(map_crc));'''
    return s.replace('endmodule',(tail if tap else " assign {summary_hit,summary,map_crc}=81'd0;")+'\nendmodule')


def put_hex(p,values):
    p.write_text(''.join(f'{v:x}\n' for v in values))


def fixtures(d,archive):
    pins=json.loads((ROOT/'analysis/body581-verification.json').read_bytes())['inputs']
    import hashlib
    total=0
    with zipfile.ZipFile(archive) as z:
        for g in range(905,958):
            data=[]
            for ext in ('geometry','raw'):
                key=f'frame{g}.{ext}'
                b=z.read('data/'+key)
                assert hashlib.sha256(b).hexdigest()==pins[key]
                data.append(b)
            maps,rows,_,_,raster,_=encode(*data,g)[2]
            n=len(maps)//33
            assert n*33==len(maps) and len(rows)==len(raster)==224
            raw=struct.pack('<'+'H'*len(maps),*maps)
            gold=[]
            for i in range(n):
                row=raw[66*i:66*(i+1)]
                gold.append((maps[33*i+32]<<48)|(maps[33*i]<<32)|binascii.crc32(row))
            base=d/f'f{g}'
            put_hex(base.with_suffix('.map'),maps)
            put_hex(base.with_suffix('.row'),[r | ((v>>49&1)<<8) for r,v in zip(rows,raster)])
            put_hex(base.with_suffix('.gold'),gold)
            base.with_suffix('.count').write_text(f'{n} {binascii.crc_hqx(raw,65535)}\n')
            total+=n
    return total


def run(a):
    checked_board(a.board)
    a.out.mkdir(parents=True,exist_ok=False)
    result={}
    for name in (('reference','tap') if a.mode=='map' else ('tap',)):
        with tempfile.TemporaryDirectory(prefix='nes598-') as tmp:
            d=Path(tmp)
            (d/(CORE+'.sv')).write_bytes(collector(a.board,name=='tap').encode())
            shutil.copy(ROOT/'rtl'/TAP,d/TAP)
            def execute(command,log):
                with (a.out/(name+'-'+log)).open('wb') as f:
                    subprocess.run(command,cwd=d,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
            pins={f:sha(d/f) for f in (CORE+'.sv',TAP)}
            if a.mode=='sim':
                n=fixtures(d,a.archive)
                tb='nes_map_seal598_tb.sv'
                shutil.copy(ROOT/'tools'/tb,d/tb)
                execute([str(Q/'vlib.exe'),'work'],'vlib.log')
                execute([str(Q/'vlog.exe'),'-sv',TAP,CORE+'.sv',tb],'vlog.log')
                execute([str(Q/'vsim.exe'),'-c','work.map_seal598_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'vsim.log')
                assert f'PASS598 frames=53 groups={n}' in (a.out/'tap-vsim.log').read_text()
                result[name]=dict(groups=n,frames=53,pins=pins,bench=sha(d/tb))
            else:
                (d/'region.qpf').write_text('PROJECT_REVISION = "region"\n')
                (d/'region.qsf').write_text(f'''set_global_assignment -name FAMILY "Cyclone IV E"
set_global_assignment -name DEVICE EP4CE15F17C8
set_global_assignment -name TOP_LEVEL_ENTITY {CORE}
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name SYSTEMVERILOG_FILE {CORE}.sv
set_global_assignment -name SYSTEMVERILOG_FILE {TAP}
''')
                execute(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','region'],'map.log')
                report=d/'output_files/region.map.rpt'
                summary=(d/'output_files/region.map.summary').read_text()
                assert 'Successful' in summary and 'Lite Edition' in summary
                shutil.copy(report,a.out/(name+'.map.rpt'))
                costs={}
                for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('bits','Total memory bits')]:
                    costs[k]=int(re.search(r'^\s*'+label+r'\s*:\s*([\d,]+)',summary,re.M)[1].replace(',',''))
                result[name]=dict(costs=costs,pins=pins,report=sha(report))
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('map','sim'))
    p.add_argument('--board',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--archive',type=Path)
    a=p.parse_args()
    if a.mode=='sim' and not a.archive:p.error('sim requires --archive')
    run(a)
