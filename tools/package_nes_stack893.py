"""Qualify the loader stack lifetime change and reuse every MMC892 board byte."""
import json
import struct
import zlib
from zipfile import ZipFile

from check_nes_game478 import Machine
from check_nes_reset796 import replay
from package_nes_trial872 import ROOT, read, sha, write_verified_archive
from prepare_nes_stack893 import WORK,SOURCE


def package():
    src=WORK/'linkC/src'
    fwpath=src/'obj-nes-100/firmware.stm'
    fw=fwpath.read_bytes()
    size,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and size+512==len(fw)<=212992 and crc==zlib.crc32(fw[512:]) and inv^crc==0xffffffff
    before,after=[read(WORK/f'final{n}.json') for n in (892,893)]
    parent=read(ROOT/'analysis/trial892-package.json')
    assert parent['ARM']==before['firmware']==after['trace_ARM']==sha(SOURCE/'obj-nes-100/firmware.stm')
    assert after['firmware']==sha(fwpath) and before['trace']==after['trace']
    assert parent['client']==before['client']==after['client']
    for k in ('first-display','bad-first-input-crc'):
        a,b=before['cases'][k],after['cases'][k]
        for field in ('transactions','steps','checked_retire','opcodes','STOP','checkpoints'):
            assert a[field]==b[field]
        assert b['checked_retire']==(k=='first-display') and b['STOP']==1
        assert b['static_gap_bytes']>0 and b['first_stack_write_to_static'] is None
    assert before['cases']['first-display']['first_stack_write_to_static']
    machine=Machine(src,bytes(128))
    for marker,expected in [('NES MMC3 893.nh1',384),('NES START 893.nh1',385),('NES BOOT 893.nh1',386),('NES MMC3 892.nh1',0)]:
        machine.u.mem_write(0x20012000,marker.encode()+b'\0')
        assert machine.call('marker_geometry',[0x20012000])==expected
    assert all(f'nes-{k}-mmc893.txt'.encode()+b'\0' in fw for k in ('progress','game-last','budget'))
    boot=replay(src,1,'defer',probe=2,pre_snapshots=[bytes.fromhex('e6000040000003')])
    assert not boot['terminal'] and boot['frame_entry']==0 and boot['records'][-1]==['PROBE_STOPPED',2,0]
    loader=read(WORK/'loader.json')
    full=read(WORK/'full-loader/result.json')
    menu=read(WORK/'menu.json')
    assert full['compared']==393216 and full['closed']==2 and full['entry_sp']==hex(0x20010000-sum(after['caller_stack_bytes']))
    assert full['firmware']==loader['firmware']==menu['firmware']==sha(fwpath)
    assert loader['cases']==parent['checks']['loader']['cases'] and menu['rows']['normal']['released']
    recovery={k:read(WORK/f'recovery-{k}/result.json') for k in ('none','program','done','busy','token')}
    assert all(r['passed'] and r['safe_return']==(key=='none') and r['firmware_sha256']==after['firmware'] for key,r in recovery.items())
    source=WORK.parent/'nes-reset892/MMC892-ADVENTURE-60SEC-SD-ROOT.zip'
    assert sha(source)==parent['ZIP_SHA256']
    with ZipFile(source) as z:
        bi=z.read(next(n for n in z.namelist() if n.endswith('/fpga_mmc892.bi3')))
    report=dict(edition=893,physical=False,ARM=after['firmware'],flash_B=len(fw),flash_free_B=212992-len(fw),
                client=after['client'],board=parent['board'],board_reused_from=892,control=before,candidate=after,
                checks=dict(loader=loader,full_loader=full,recovery=recovery,menu=menu,boot=boot),
                scope='First cold opening fixture and CRC rejection. Peripheral and tick models. No hardware FPS or all-frame stack bound.')
    write_verified_archive(WORK,parent,fw,bi,report,source=source)


if __name__=='__main__':
    package()
