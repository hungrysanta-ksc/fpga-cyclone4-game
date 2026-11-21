"""Build the final 890 ARM and the 889 consumer on the physically tested 872 board."""
import argparse
from pathlib import Path
import shutil
import struct
from types import SimpleNamespace
import zlib

from nes_bulk889 import BASE, WORK as READER
from package_nes_trial704 import digest, image, read, save, sha
from package_nes_trial855 import board_proof, loader
from package_nes_trial872 import QUARTUS, ROOT, compile_board, write_verified_archive
from prepare_nes_trial802 import rename_edition
from check_nes_strip869 import metrics
from check_nes_retire878 import verify_retire_order
from analyze_nes_transition850 import STRIDE

WORK=BASE.parent/'nes-trial890'
SRC=WORK/'link-credit/src'
CLIENT=WORK/'client02'


def prepare():
    parent=read(ROOT/'analysis/bulk889-results.json')
    assert sha(BASE/'link-credit/src/obj-nes-100/firmware.stm')==parent['firmware']
    assert sha(READER/'client03/sink165.sfc')==parent['consumer']
    rename_edition(BASE/'link-credit/src',WORK/'patch',872,890)
    shutil.copytree(READER/'client03',CLIENT)


def board(temp):
    reference=read(ROOT/'analysis/trial872-package.json')
    candidate=read(ROOT/'analysis/bulk889-results.json')
    compile_board(temp,'872','890',CLIENT,reference['board']['image']['SOF'],candidate['consumer'])
    pack_board(temp)


def pack_board(temp):
    image(SimpleNamespace(board=temp/'nes-trial816-board890',out=temp/'nes-trial890-packed',quartus=QUARTUS,number='890'))


def qualification(temp):
    previous=read(ROOT/'analysis/bulk889-results.json')
    reference=read(ROOT/'analysis/trial872-package.json')
    firmware=(SRC/'obj-nes-100/firmware.stm').read_bytes()
    old=(BASE/'link-credit/src/obj-nes-100/firmware.stm').read_bytes()
    assert digest(old)==previous['firmware'] and firmware[32:]==old[32:].replace(b'872',b'890')
    size,crc,inverse=struct.unpack_from('<III',firmware,8)
    assert firmware[:4]==b'STM3' and len(firmware)==size+512<=212992
    assert crc==zlib.crc32(firmware[512:]) and crc^inverse==0xffffffff
    for name in ('NES MMC3 890.nh1','mmc890.nes','fpga_mmc890.bi3','nes-budget-mmc890.txt',
                 'nes-progress-mmc890.txt','nes-game-last-mmc890.txt'):
        assert name.encode()+b'\0' in firmware
    fw=digest(firmware)
    client=sha(CLIENT/'sink165.sfc')
    assert client==previous['consumer']
    clips={}
    for scene in ('opening','transition','demo'):
        for phase in (1,2):
            prefix=f'nes-tile821-{scene}-jointmirror-p{phase}-'
            original=temp/(prefix+'889-reader')
            final=temp/(prefix+'890-final')
            run=read(final/'joint.json')
            ref=read(original/'joint.json')
            assert run['firmware_SHA256']==fw and run['client_SHA256']==client
            assert run['parameters']==ref['parameters'] and run['passed'] and run['last_status']==1
            assert verify_retire_order(final)==run['commits']==ref['commits']
            traces={name:sha(final/name) for name in ('events.json','packets.jsonl','window.csv')}
            for name,checksum in traces.items():
                assert sha(original/name)==checksum,(scene,phase,name)
            for frame in run['frames']:
                g=frame['generation']
                a,b=[(p/f'frame-{g}.rgb').read_bytes() for p in (original,final)]
                assert len(a)==len(b) and a[7*STRIDE:231*STRIDE]==b[7*STRIDE:231*STRIDE]
                assert sha(original/f'map-{g}.bin')==sha(final/f'map-{g}.bin')
            row=metrics(final)
            prior=previous['scenes'][scene][f'{phase}-889-reader']
            key=f'{scene}-{phase}'
            assert all(row[k]==prior[k] for k in ('after_two_VBlanks','last_ACK','opening_marks','held_blank_VBlanks'))
            delta=row['last_ACK']-reference['final_link_runs'][key]['last_ACK']
            clips[key]=dict(intervals=row['after_two_VBlanks'],pictures=row['pictures'],last_ACK=row['last_ACK'],
                            ACK_delta_clocks=delta,opening_marks=row['opening_marks'],trace_SHA256=traces)
            if scene=='demo':
                assert row['after_two_VBlanks']==138 and delta<0
            if scene=='transition':
                assert row['after_two_VBlanks']==119
            if scene=='opening':
                assert row['opening_marks']['910']==[59,231] and row['after_two_VBlanks']==121
    checks={k:read(WORK/(k+'.json')) for k in ('timer','loader','windows','retire','menu','input','guards')}
    assert all(checks[k]['firmware']==fw for k in ('timer','menu','loader','input'))
    assert checks['retire']['ARM']==checks['windows']['firmware_SHA256']==fw
    assert checks['windows']['unfinished_excluded'] and [(r['start_s'],r['end_s']) for r in checks['windows']['accepted']]==[(1,30),(30,60)]
    assert checks['timer']['passed'] and checks['menu']['rows']['normal']['released']
    assert checks['input']['cases']==reference['checks']['input-guards']['cases']
    assert checks['timer']['cases']==reference['checks']['timer']['cases']
    assert checks['retire']['cases']==read(BASE/'retire.json')['cases']
    assert checks['guards']['client']==client and all(checks['guards'][k]==previous['guards'][k]
           for k in ('cases','bad_tiles','two_column_cancel'))
    assert checks['loader']['rom']==reference['checks']['loader']['rom'] and checks['loader']['cases']==reference['checks']['loader']['cases']
    boot=read(temp/'nes-trial890-boot/result.json')
    assert boot['passed'] and sorted((r['fault'],r['kind']) for r in boot['cases'] if r['ROM']==client)==[(False,'restored'),(True,'rejected')]
    base=read(WORK/'base/result.json')
    assert base['passed'] and base['base_restored'] and base['safe_return'] and base['firmware_sha256']==fw
    assert base['config_paths']==['/sd2snes/fpga_mmc890.bi3','/sd2snes/fpga_base.bi3']
    checks.update(base=base,boot=boot)
    return firmware,clips,checks


def package(temp):
    fw,clips,checks=qualification(temp)
    reference=read(ROOT/'analysis/trial872-package.json')
    proof,bitstream=board_proof(temp,reference['board'],'890',CLIENT,'872')
    old=temp/'nes-trial816-board872'
    new=temp/'nes-trial816-board890'
    inputs=[p for sub in ('rtl','sys') for p in (old/sub).rglob('*') if p.is_file()]
    inputs.extend(p for p in old.iterdir() if p.suffix in ('.sv','.v','.vhd','.qpf','.qsf','.sdc','.tcl','.hex'))
    changed=[p.relative_to(old).as_posix() for p in inputs if sha(p)!=sha(new/p.relative_to(old))]
    assert changed==['sink-program.hex']
    proof['compared_board_inputs']=len(inputs)
    proof['changed_board_inputs']=changed
    rom=(CLIENT/'sink165.sfc').read_bytes()
    assert digest(rom[:5056]+rom[-64:])==proof['ROM_bus']
    report=dict(edition=890,physical=False,ARM=digest(fw),client=digest(rom),
                flash_B=len(fw),flash_free_B=212992-len(fw),board=proof,final_link_runs=clips,checks=checks)
    write_verified_archive(WORK,reference,fw,bitstream,report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','board','image','loader','guards','pack'))
    p.add_argument('path',nargs='?',type=Path)
    a=p.parse_args()
    if a.action=='prepare':
        prepare()
    elif a.path is None:
        p.error('provide the ROM path for loader or the replay root for board/guards/pack')
    elif a.action=='board':
        board(a.path)
    elif a.action=='image':
        pack_board(a.path)
    elif a.action=='loader':
        loader(a.path,SRC,890,WORK)
    elif a.action=='guards':
        from guard_nes_bulk889 import verify
        save(WORK/'guards.json',verify(a.path,'890-final',WORK,'client02'))
    else:
        package(a.path)
