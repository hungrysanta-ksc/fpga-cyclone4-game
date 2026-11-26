"""Package matched receiver probes using the two unchanged, hardware-tested FPGA images."""
import struct
import sys
import zlib
from zipfile import ZipFile

from check_nes_kirby1024_journal import replay
from check_nes_kirby1025_sampling import check
from package_nes_trial872 import ROOT, PROBES, digest, read, write_verified_archive


def package(edition):
    parent={1029:1025,1030:1028}[edition]
    work=PROBES/f'nes-kirby{edition}'
    previous=read(ROOT/f'analysis/trial{parent}-package.json')
    source=PROBES/f'nes-kirby{parent}/MMC{parent}-KIRBY-60SEC-SD-ROOT.zip'
    with ZipFile(source) as z:
        name,=[n for n in z.namelist() if n.endswith(f'/fpga_mmc{parent}.bi3')]
        board=z.read(name)
    assert digest(board)==previous['board_BI3']
    def firmware(n):
        return (PROBES/f'nes-kirby{n}/link/src/obj-nes-100/firmware.stm').read_bytes()
    fw=firmware(edition)
    size,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==size+512<=212992 and crc==inv^0xffffffff==zlib.crc32(fw[512:])
    a,b=firmware(1029)[512:],firmware(1030)[512:]
    # The row ABI's 16-bit edition is the low half of a word literal after magic 0x9001.
    marker=lambda n:struct.pack('<HH',0x9001,n)
    assert a.count(marker(1029))==1 and a.replace(b'1029',b'1030').replace(marker(1029),marker(1030))==b
    for s in [f' {edition}.nh1',f'mmc{edition}.nes',f'fpga_mmc{edition}.bi3',f'nes-frame-mmc{edition}.bin',
              *(f'nes-{k}-mmc{edition}.txt' for k in ('game-last','budget','progress'))]:
        assert s.encode()+b'\0' in fw
    proofs={k:read(work/'proof'/f'{k}.json') for k in ('trace','windows','sram','timer','menu','base-result','loader')}
    assert proofs['trace']['checked_row_copy'] and proofs['sram']['cases']['normal']['checked_retire']
    cases=proofs['sram']['cases']
    records=cases['normal']['input_observer']
    assert records==cases['1247-empty-offers']['input_observer'] and not cases['bad-crc']['input_observer']
    assert 'bad-crc' in proofs['sram']['cases'] and proofs['loader']['bad-last']['error']==4
    assert proofs['timer']['passed'] and proofs['menu']['rows']['normal']['released'] and proofs['base-result']['safe_return']
    assert digest(fw)==proofs['timer']['firmware']==proofs['menu']['firmware']==proofs['base-result']['firmware_sha256']==proofs['windows']['firmware_SHA256']
    sampling=check(edition)
    journal=replay(work,edition,[])
    assert journal['firmware']==sampling['firmware']==digest(fw) and journal['end'][0]=='MENU_PREPARED'
    report=dict(edition=edition,physical=False,board_BI3=digest(board),board_edition=parent,firmware=digest(fw),
                flash_B=len(fw),flash_free_B=212992-len(fw),sampling=sampling,journal=journal,
                pair_code_identical_except_edition=True,guarded_input=proofs['trace'],linked_input_records=records,
                timer_stop=True,menu_release=True,SRAM_D0=True)
    write_verified_archive(work,previous,fw,board,report,source=source,game_label='KIRBY')


if __name__=='__main__':
    package(int(sys.argv[1]))
