"""Package only the routed input-timing candidate with its final checked ARM."""
import struct
import zlib
from pathlib import Path
from check_nes_opening818 import admission
from cross_nes1022 import rom_path
from package_nes_kirby1027 import programmer,timing
from package_nes_trial872 import ROOT, digest, read, write_verified_archive
from prepare_nes_kirby1035 import BASE
from read_nes_kirby1034 import CAPACITY,HEADER,INGRESS,OFFSET,ROW,SIZE,decode

WORK=BASE.parents[1]/'nes-kirby1035'


def check_layout(sample):
    data=bytearray(SIZE)
    h=bytes.fromhex(sample)
    gen=int.from_bytes(h[2:4],'little')
    HEADER.pack_into(data,0,0x9001,1035,0,1,0,0,ROW.size,CAPACITY)
    desc=struct.pack('<BBHHH',1,1,96,416,gen)+h[12:16]
    ROW.pack_into(data,HEADER.size,5970,gen,666,1800,10,5,16,0,7,1,h,desc)
    def case(start,off,lag):
        INGRESS.pack_into(data,OFFSET,10,500000,490000,900,lag<<16|0x8080|off<<8|start,1<<24|1849,gen,17)
        return decode(bytes(data),1035)['rows'][0]
    good=case(5,37,4000)
    assert good['second_bank_after_first_return_ticks']==dict(waiting_for_publication=0,published_head_to_return=3)
    assert good['previous_commit_D2_response_ms'][1]<good['first_D1_call_ms'][1]
    assert good['previous_collector_release_ms'][1]<good['capture_start_ms'][1]<good['first_block_ready_ms'][1]
    cold=case(127,127,65535)
    assert cold['capture_start_ms']==[None,None] and cold['previous_commit_D2_response_ms'] is None
    # Swap bank publication past retirement: generation and token still match.
    data[HEADER.size+16+9]=h[24+1]+1
    assert 'unresolved' in decode(bytes(data),1035)['rows'][0]
    return good


def package():
    src=WORK/'link/src'
    fw=(src/'obj-nes-100/firmware.stm').read_bytes()
    size,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and size+512==len(fw)<=212992 and crc==inv^0xffffffff==zlib.crc32(fw[512:])
    assert all((s+'\0').encode() in fw for s in (' 1035.nh1','mmc1035.nes','fpga_mmc1035.bi3',
               'nes-frame-mmc1035.bin',*(f'nes-{k}-mmc1035.txt' for k in ('budget','progress','game-last'))))
    arm=read(WORK/'proof/return.json')
    base=read(WORK/'proof/base-result.json')
    assert base['safe_return'] and base['firmware_sha256']==arm['menu']['firmware']==arm['timer']['firmware']==digest(fw)
    assert arm['windows']==75 and arm['timer']['passed'] and arm['menu']['rows']['normal']['released']
    assert arm['journal']['end'][0]=='MENU_PREPARED' and arm['cases']['normal']['checked_retire']
    assert not arm['cases']['bad-crc']['input_observer']
    banks=read(WORK/'banks.json')
    sample=check_layout(banks['header'])
    rtl=read(WORK/'comparison.json')
    assert len(rtl['cases'])==18 and all('PASS1035' in r['result'] for r in rtl['cases'])
    image=rom_path(Path.home()/'Downloads/test','kirby').read_bytes()
    loader={}
    for name,data,error in [('kirby',image,0),('bad-last',image[:-1]+bytes([image[-1]^1]),4)]:
        loader[name]=admission(src,data,1035)
        assert loader[name]==dict(program=error==0,read_B=len(image),error=error)
    routed=WORK/'lite-times'
    cost=timing(routed)
    bitstream,pgm=programmer(routed,WORK,1035)
    report=dict(edition=1035,parent=1034,physical=False,firmware=digest(fw),flash_B=len(fw),flash_free_B=212992-len(fw),
                board_BI3=digest(bitstream),SOF=digest((routed/'board.sof').read_bytes()),**cost,
                programmer=pgm,loader=loader,checked_layout=sample,banks=banks,export_replay=rtl,
                base_recovery=True,menu_release=True,timer_stop=True,bad_crc_rejected=True,sampled_windows=75,
                observed_physical_4_to_3=None,observed_physical_ACK_gain_ms=None)
    write_verified_archive(WORK,read(ROOT/'analysis/trial1034-package.json'),fw,bitstream,report,
                           source=BASE.parent/'MMC1034-KIRBY-60SEC-SD-ROOT.zip',game_label='KIRBY')


if __name__=='__main__':package()
