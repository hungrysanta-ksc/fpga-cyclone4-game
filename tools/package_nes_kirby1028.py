"""Qualify the performance-board prefetch overlay and the identically sampled ARM."""
import argparse
import struct
import zlib
from pathlib import Path

from prepare_nes_kirby1028 import ROOT, WORK, PROBES
from check_nes_kirby1025_sampling import check
from check_nes_kirby1024_journal import replay
from package_nes_kirby1027 import programmer, timing
from package_nes_trial872 import read, digest, write_verified_archive
from summarize_nes_kirby1028 import summarize

def package(downloads):
    evidence=summarize(downloads)
    routed=WORK/'lite-perf'
    board=timing(routed)
    old=PROBES/'nes-kirby1023/board'
    new=WORK/'board-perf'
    old_files={p.relative_to(old) for p in old.rglob('*') if p.is_file()}
    assert old_files=={p.relative_to(new) for p in new.rglob('*') if p.is_file()}
    assert [p.as_posix() for p in old_files if (old/p).read_bytes()!=(new/p).read_bytes()]==['nes_e9_rows914.sv']
    src=WORK/'link/src'
    fw=(src/'obj-nes-100/firmware.stm').read_bytes()
    size,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==512+size<=212992 and zlib.crc32(fw[512:])==crc==inv^0xffffffff
    for n in (' 1028.nh1','mmc1028.nes','fpga_mmc1028.bi3','nes-frame-mmc1028.bin',
              *(f'nes-{k}-mmc1028.txt' for k in ('progress','budget','game-last'))):
        assert n.encode()+b'\0' in fw
    ref=read(ROOT/'analysis/trial1025-package.json')
    assert len(fw)==ref['flash_B']
    proof={k:read(WORK/'proof'/f'{k}.json') for k in ('loader','sram','timer','base-result','menu','trace','windows')}
    assert all(proof[k]['firmware']==digest(fw) for k in ('menu','timer'))
    assert proof['windows']['firmware_SHA256']==proof['base-result']['firmware_sha256']==digest(fw)
    assert proof['sram']['cases']['normal']['checked_retire'] and 'bad-crc' in proof['sram']['cases']
    assert proof['loader']['kirby']['program'] and proof['loader']['bad-last']['error']==4
    assert proof['timer']['passed'] and proof['menu']['rows']['normal']['released'] and proof['base-result']['safe_return']
    assert proof['trace']['reset']
    sampling=check(1028)
    journal=replay(WORK,1028,[])
    assert journal['firmware']==sampling['firmware']==digest(fw) and journal['end'][0]=='MENU_PREPARED'
    assert sampling['windows']==sampling['wire_reads']==75
    packed,pgm=programmer(routed,WORK,1028)
    report=dict(edition=1028, physical=False, firmware=digest(fw), flash_B=len(fw), flash_free_B=212992-len(fw),
                board_BI3=digest(packed),SOF=digest((routed/'board.sof').read_bytes()),**board,
                programmer=pgm,journal=journal,sampling=sampling,reference_performance=1024,reference_sampling=1025,
                loader=proof['loader'],base_safe_return=True,menu_released=True,stop_timer=True,
                sram_checked_retire=True,crc_rejected=True,diagnostic_fit_LAB_required=966,
                replay_done_deltas_ms=[c['advance_final_tile_ms'] for c in evidence['cases']])
    write_verified_archive(WORK,ref,fw,packed,report,
                          source=PROBES/'nes-kirby1025/MMC1025-KIRBY-60SEC-SD-ROOT.zip',game_label='KIRBY')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('downloads',type=Path)
    package(p.parse_args().downloads)
