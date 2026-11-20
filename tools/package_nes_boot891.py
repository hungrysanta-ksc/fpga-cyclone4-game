"""Qualify the boot observer using the delivered 890 software and a filename-only relink."""
import argparse
from pathlib import Path
import re
import struct
from types import SimpleNamespace
import zlib

from package_nes_trial890 import CLIENT, SRC, WORK as PREVIOUS
from package_nes_trial704 import digest, image, read, sha
from package_nes_trial855 import board_proof, loader
from package_nes_trial872 import QUARTUS, ROOT, write_verified_archive
from prepare_nes_trial802 import rename_edition


WORK=PREVIOUS.parent/'nes-trial891'
VARIANT='891E'


def marker_modes():
    from check_nes_game478 import Machine
    machine=Machine(WORK/'link-credit/src',bytes(128))
    modes={}
    for name,expected in [('NES-DIAG/NES BOOT 891.nh1',386),('NES START 891.nh1',385),
                          ('NES MMC3 891.nh1',384),('NES BOOT 890.nh1',0)]:
        machine.u.mem_write(0x20012000,name.encode()+b'\0')
        modes[name]=machine.call('marker_geometry',[0x20012000])
        assert modes[name]==expected
    return modes


def package(temp, cases):
    ref=read(ROOT/'analysis/trial890-package.json')
    old=(SRC/'obj-nes-100/firmware.stm').read_bytes()
    fw=(WORK/'link-credit/src/obj-nes-100/firmware.stm').read_bytes()
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    assert digest(old)==ref['ARM'] and fw[:4]==b'STM3' and size+512==len(fw)<=212992
    assert zlib.crc32(fw[512:])==crc and crc^inverse==0xffffffff
    # Includes the ARM instructions, data and all user-visible path strings.
    assert fw[32:]==old[32:].replace(b'890',b'891')
    assert sha(CLIENT/'sink165.sfc')==ref['client']
    old_board=temp/'nes-trial816-board890'
    new_board=temp/f'nes-trial816-board{VARIANT}'
    def io_inventory(board):
        text=(board/'output_files/board.sta.rpt').read_text(errors='replace')
        # Both setup and hold tables, retaining table order and duplicate ports.
        ports=re.findall(r'^; (\S+)\s+; No (input|output) delay,',text,re.M)
        fanouts=set((board/'boot891-inputs.tsv').read_text().splitlines())
        assert ports and len(fanouts)>9000
        return ports,fanouts
    old_ports,old_edges=io_inventory(old_board)
    new_ports,new_edges=io_inventory(new_board)
    assert old_ports==new_ports
    added=sorted(e for e in new_edges-old_edges if e.partition('\t')[0] not in ('CLKIN','SNES_SYSCLK'))
    assert added==['SNES_ROMSEL_IN\tnes_screen_status151:screen_status|select_sync[0]']
    proof,bitstream=board_proof(temp,ref['board'],VARIANT,CLIENT,'890',expected_input_paths=(664,557))
    proof['new_nonclock_input_fanouts']=added
    inputs=[p for sub in ('rtl','sys') for p in (old_board/sub).rglob('*') if p.is_file()]
    audit_scripts={'boot891-inputs.tcl','boot891-inputs2.tcl'}
    inputs.extend(p for p in old_board.iterdir() if p.suffix in ('.sv','.v','.vhd','.qpf','.qsf','.sdc','.tcl','.hex')
                  and p.name not in audit_scripts)
    assert len(inputs)==ref['board']['compared_board_inputs']
    changed=[p.relative_to(old_board).as_posix() for p in inputs if sha(p)!=sha(new_board/p.relative_to(old_board))]
    assert changed==['nes_screen_status151.sv']
    assert sha(cases/'nes_screen_status151.sv')==sha(new_board/changed[0])
    runs=read(cases/'result.json')
    assert runs['872']['cases']==runs['890']['cases'] and len(runs['891']['cases'])==28
    for old,new in zip(runs['890']['cases'],runs['891']['cases'],strict=True):
        assert all(old[k]==new[k] for k in old if k!='order')
    load=read(WORK/'loader.json')
    assert load['firmware']==digest(fw) and load['cases']==ref['checks']['loader']['cases']
    base=read(WORK/'base/result.json')
    menu=read(WORK/'menu.json')
    assert base['firmware_sha256']==menu['firmware']==digest(fw)
    assert base['passed'] and base['base_restored'] and base['safe_return']
    assert base['config_paths']==['/sd2snes/fpga_mmc891.bi3','/sd2snes/fpga_base.bi3']
    assert menu['rows']['normal']['released']
    report=dict(edition=891,physical=False,scope='Boot diagnosis; no new FPS measurement',
                ARM=digest(fw),client=ref['client'],flash_B=len(fw),flash_free_B=212992-len(fw),
                board=proof,changed_board_inputs=changed,status_RTL=sha(new_board/changed[0]),
                cases_per_board=28,checks=dict(loader=load,base=base,menu=menu,markers=marker_modes()))
    write_verified_archive(WORK,ref,fw,bitstream,report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','loader','image','pack'])
    p.add_argument('path',nargs='?',type=Path)
    p.add_argument('--cases',type=Path)
    a=p.parse_args()
    if a.action=='prepare':
        rename_edition(SRC,WORK/'patch',890,891)
    elif a.action=='loader':
        loader(a.path,WORK/'link-credit/src',891,WORK)
    elif a.action=='image':
        image(SimpleNamespace(board=a.path/f'nes-trial816-board{VARIANT}',
                              out=a.path/f'nes-trial{VARIANT}-packed',quartus=QUARTUS,number=VARIANT))
    else:
        package(a.path,a.cases)
