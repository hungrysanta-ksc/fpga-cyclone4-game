"""Qualify each member of the matched ready-age comparison on its own routed board."""
import struct
import sys
import zlib

from check_nes_kirby1024_journal import replay
from check_nes_kirby1025_sampling import check
from package_nes_kirby1027 import programmer, timing
from package_nes_trial872 import ROOT, PROBES, digest, read, write_verified_archive


def package(edition):
    parent={1031:1030,1032:1029}[edition]
    work=PROBES/f'nes-kirby{edition}'
    def image(n):
        return (PROBES/f'nes-kirby{n}/link/src/obj-nes-100/firmware.stm').read_bytes()
    fw=image(edition)
    length,crc,inverse=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==length+512<=212992 and crc==inverse^0xffffffff==zlib.crc32(fw[512:])
    marker=lambda n:struct.pack('<HH',0x9001,n)
    a=image(1031)[512:]
    assert a.count(marker(1031))==1 and a.replace(b'1031',b'1032').replace(marker(1031),marker(1032))==image(1032)[512:]
    names=[f' {edition}.nh1',f'mmc{edition}.nes',f'fpga_mmc{edition}.bi3',f'nes-frame-mmc{edition}.bin',
           *(f'nes-{k}-mmc{edition}.txt' for k in ('budget','progress','game-last'))]
    assert all(n.encode()+b'\0' in fw for n in names)
    base=PROBES/('nes-kirby1028/board-perf' if edition==1031 else 'nes-kirby1023/board')
    board=work/('board' if edition==1031 else 'board-bus')
    files={p.relative_to(board) for p in board.rglob('*') if p.is_file()}
    assert files=={p.relative_to(base) for p in base.rglob('*') if p.is_file()}
    changed={'nes_native_spi165.sv'}
    if edition==1032:
        changed.update(['nes_sink_bridge165.sv','nes_sink_bus165.sv','nes_screen_status151.sv','fxpak_nes_screen137_top.sv'])
        status=(work/'bus-test/status.log').read_text()
        assert 'PASS1027_STATUS 346 SPI73 bits' in status and 'PASS1027_BUS 10966 observed clocks' in status
    assert (board/'nes_native_spi165.sv').read_bytes()==(PROBES/'nes-kirby1031/board/nes_native_spi165.sv').read_bytes()
    assert {str(p) for p in files if (board/p).read_bytes()!=(base/p).read_bytes()}==changed
    proof={k:read(work/'proof'/f'{k}.json') for k in ('age','trace','loader','timer','menu','base-result','windows')}
    observed=proof['age']
    assert observed['ARM_age_bins']=={'905':observed['RTL']['1830-2']['age'],'906':127} and len(observed['RTL'])==8
    cases=observed['ARM_cases']
    assert cases['normal']['checked_retire'] and cases['normal']['input_observer']==cases['1247-empty-offers']['input_observer']
    assert not cases['bad-crc']['input_observer'] and proof['trace']['checked_row_copy']
    assert proof['loader']['kirby']['program'] and proof['loader']['bad-last']['error']==4
    assert proof['timer']['passed'] and proof['menu']['rows']['normal']['released'] and proof['base-result']['safe_return']
    sha=digest(fw)
    assert sha==proof['timer']['firmware']==proof['menu']['firmware']==proof['windows']['firmware_SHA256']==proof['base-result']['firmware_sha256']
    sampling=check(edition)
    journal=replay(work,edition,[])
    assert sampling['firmware']==journal['firmware']==sha and sampling['wire_reads']==75 and journal['end'][0]=='MENU_PREPARED'
    routed=work/('lite' if edition==1031 else 'lite-bus')
    cost=timing(routed)
    bitstream,pgm=programmer(routed,work,edition)
    report=dict(edition=edition,physical=False,parent=parent,firmware=sha,flash_B=len(fw),flash_free_B=212992-len(fw),
                board_BI3=digest(bitstream),SOF=digest((routed/'board.sof').read_bytes()),**cost,
                programmer=pgm,simulated_first_blocks=observed['RTL'],age_oracle=observed['ARM_age_bins'],
                guarded_input=proof['trace'],linked_input_records=cases['normal']['input_observer'],sampling=sampling,
                journal=journal,SRAM_D0=True,timer_stop=True,menu_release=True,base_recovery=True,
                pair_arm_identical_except_edition=True)
    previous=read(ROOT/f'analysis/trial{parent}-package.json')
    source=PROBES/f'nes-kirby{parent}/MMC{parent}-KIRBY-60SEC-SD-ROOT.zip'
    write_verified_archive(work,previous,fw,bitstream,report,source=source,game_label='KIRBY')


if __name__=='__main__':
    package(int(sys.argv[1]))
