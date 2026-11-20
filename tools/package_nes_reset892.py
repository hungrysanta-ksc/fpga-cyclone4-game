"""Qualify the final ARM link with the MMC891 FPGA and 65816 and write the SD kit."""
import argparse
from pathlib import Path
import struct
import zlib

from guard_nes_reset892 import verify
from nes_reset892 import PROBES,ROOT,WORK
from package_nes_trial704 import digest,read,sha
from package_nes_trial855 import board_proof
from package_nes_trial872 import write_verified_archive
from check_nes_game478 import Machine


def package(temp,sim):
    ref=read(ROOT/'analysis/trial891-package.json')
    client=PROBES/'nes-trial890/client02'
    board,bi=board_proof(temp,ref['board'],'892',client,'891E')
    assert digest(bi)==ref['board']['image']['BI3']
    assert board['image']['RBF']==ref['board']['image']['RBF'] and sha(client/'sink165.sfc')==ref['client']
    src=WORK/'link/src'
    fw=(src/'obj-nes-100/firmware.stm').read_bytes()
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==size+512<=212992
    assert zlib.crc32(fw[512:])==crc and crc^inverse==0xffffffff
    cpu=Machine(src,bytes(128))
    for marker,mode in [('NES BOOT 892.nh1',386),('NES START 892.nh1',385),
                        ('NES MMC3 892.nh1',384),('NES BOOT 891.nh1',0)]:
        cpu.u.mem_write(0x20012000,marker.encode()+b'\0')
        assert cpu.call('marker_geometry',[0x20012000])==mode
    for label in ('budget','progress','game-last'):
        assert f'nes-{label}-mmc892.txt'.encode()+b'\0' in fw
    rows=read(sim/'result.json')
    assert len(rows)==12 and {(int(r['mode']),int(r['phase'])) for r in rows}=={
        (m,p) for m in range(3) for p in range(4)}
    for r in rows:
        if r['mode']=='0':
            assert r['witness']=='03' and r['stage']=='00' and r['lo_host']==r['lo_tag']==r['hi_drive']=='-1'
        else:
            assert r['witness']=='6f' and r['stage']=='01' and int(r['code_reads'])==20
            for k in ('lo','hi'):
                assert 0<int(r[k+'_host'])<=int(r[k+'_tag'])==int(r[k+'_drive'])<=118
    verify(sim)
    arm=read(WORK/'arm.json')
    base=read(WORK/'base/result.json')
    menu=read(WORK/'menu.json')
    loader=read(WORK/'loader.json')
    assert base['firmware_sha256']==menu['firmware']==loader['firmware']==arm['firmware']==digest(fw)
    assert base['passed'] and base['base_restored'] and base['safe_return'] and menu['rows']['normal']['released']
    assert base['config_paths']==['/sd2snes/fpga_mmc892.bi3','/sd2snes/fpga_base.bi3']
    assert loader['cases']==ref['checks']['loader']['cases']
    report=dict(edition=892,physical=False,ARM=digest(fw),client=ref['client'],board=board,
                flash_B=len(fw),flash_free_B=212992-len(fw),spi_hz=2625000,nes_clock_period_ns=46.566,
                scope='START and clocks supplied; real cold RAM clear and board pins; CPU opcode/write replay; linked ARM snapshot replay and modeled GPIO/STOP/base',
                boot_cases=rows,cpu_trace_sha256=sha(sim/'cpu.txt'),arm_cases=arm['rows'],prior_arm=arm['reference'],
                checks=dict(loader=loader,menu=menu,base=base))
    write_verified_archive(WORK,ref,fw,bi,report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('sim',type=Path)
    a=p.parse_args()
    package(a.temp,a.sim)
