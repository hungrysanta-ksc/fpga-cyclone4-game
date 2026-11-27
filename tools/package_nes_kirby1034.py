"""Package the checked MMC1034 ARM and timing-closed observer for a paired physical run."""
import struct
import zlib

from check_nes_opening818 import admission
from cross_nes1022 import rom_path
from pathlib import Path
from package_nes_kirby1027 import programmer, timing
from package_nes_trial872 import ROOT, PROBES, digest, read, write_verified_archive


if __name__ == '__main__':
    work=PROBES/'nes-kirby1034'
    src=work/'link/src'
    routed=work/'lite-shared'
    fw=(src/'obj-nes-100/firmware.stm').read_bytes()
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    sha=digest(fw)
    assert fw[:4]==b'STM3' and size+512==len(fw)<=212992 and crc==inverse^0xffffffff==zlib.crc32(fw[512:])
    names=[' 1034.nh1','mmc1034.nes','fpga_mmc1034.bi3','nes-frame-mmc1034.bin',
           *(f'nes-{k}-mmc1034.txt' for k in ('budget','progress','game-last'))]
    assert all(n.encode()+b'\0' in fw for n in names)
    evidence=read(work/'proof/qualification.json')
    base=read(work/'proof/base-result.json')
    assert base['safe_return'] and base['firmware_sha256']==sha
    assert evidence['sampled_windows']==75 and evidence['timer']['firmware']==evidence['menu']['firmware']==sha
    assert evidence['journal']['end'][0]=='MENU_PREPARED' and evidence['checked_header']['E9_list_complete']
    cases=read(work/'proof/age.json')['ARM_cases']
    assert cases['normal']['checked_retire'] and cases['normal']['input_observer']==cases['1247-empty-offers']['input_observer']
    assert not cases['bad-crc']['input_observer']
    image=rom_path(Path.home()/'Downloads/test','kirby').read_bytes()
    loader={}
    for name,data,error in [('kirby',image,0),('bad-last',image[:-1]+bytes([image[-1]^1]),4)]:
        loader[name]=admission(src,data,1034)
        assert loader[name]==dict(program=error==0,read_B=len(image),error=error)
    cost=timing(routed)
    bitstream,pgm=programmer(routed,work,1034)
    inputs=read(ROOT/'analysis/trial1032-package.json')
    report=dict(edition=1034,physical=False,parent=1032,firmware=sha,flash_B=len(fw),flash_free_B=212992-len(fw),
                board_BI3=digest(bitstream),SOF=digest((routed/'board.sof').read_bytes()),**cost,
                programmer=pgm,loader=loader,fixture=evidence['checked_header'],sampled_windows=evidence['sampled_windows'],
                checked_input=cases['normal']['input_observer'],bad_crc_rejected=True,base_recovery=True,menu_release=True,
                timer_stop=True,SRAM_D0=True)
    write_verified_archive(work,inputs,fw,bitstream,report,
                           source=PROBES/'nes-kirby1032/MMC1032-KIRBY-60SEC-SD-ROOT.zip',game_label='KIRBY')
