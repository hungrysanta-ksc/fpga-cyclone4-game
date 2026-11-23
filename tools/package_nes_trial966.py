"""Assemble the 60-second Adventure Island IV trial from the verified 964 board and link."""
import argparse
import re
import shutil
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from check_nes_blank959 import directory, read, rows, sha
from nes_arm964 import ARM
from nes_blank960 import PACKED
from package_nes_trial704 import digest, image
from package_nes_trial872 import write_verified_archive
from prepare_nes_frame900 import QUARTUS
from prepare_nes_trial802 import rename_edition

ROOT = Path(__file__).resolve().parents[1]
WORK = ARM.with_name('nes-trial966')


def prepare():
    assert sha(ARM/'link/src/obj-nes-100/firmware.stm') == read(ROOT/'analysis/mail964-results.json')['firmware']
    shutil.copytree(ARM/'link', WORK/'link')
    src = WORK/'link/src'
    rename_edition(src, WORK/'markers', 955, 966)
    for path in (WORK/'markers').iterdir():
        shutil.copyfile(path, src/path.name)
    budget = src/'nes_budget210.c'
    body = budget.read_bytes()
    assert body.count(b'log900p->edition=955;') == 1
    budget.write_bytes(body.replace(b'log900p->edition=955;', b'log900p->edition=966;'))


def make_image(temp):
    board = temp/'nes-trial816-board964'
    reports = read(ROOT/'analysis/mail964-results.json')['board']['reports']
    for name, checksum in reports.items():
        assert sha(board/'output_files'/name) == checksum
    image(SimpleNamespace(board=board, quartus=QUARTUS, out=temp/'nes-image966-release', number='966'))


def guards(game):
    import check_nes_header950 as header
    from check_nes_supply905_arm import run
    from nes_order938 import empty_next_offer
    run(game, WORK, 966, short_header=True, order=empty_next_offer, marker_values=(4,8,16,24))
    with patch.object(header, 'work', lambda _: WORK):
        header.test('release')


def replay(temp,phase,cache):
    from nes_verified965 import run
    from nes_feedback953 import evidence
    tail = None
    if (phase,cache) == (1,'cold'):
        tail = evidence(directory(temp,1,'965wire5','cold'),910,log_name='mail964.log')
    record = read(ROOT/'analysis/credit965-wire.json')[str(phase)]
    run(temp,phase,cache,record,tail=tail,work=WORK,edition=966,tag='966release')


def checked_cases(temp,firmware,client):
    from check_nes_blank959 import summary
    from analyze_nes_tail961 import milliseconds
    from read_nes_supply905 import decode
    record = read(ROOT/'analysis/credit965-results.json')['phases']
    cases = {}
    for phase in (1,2):
        for cache in ('warm','cold'):
            case = record[str(phase)][cache]
            adjusted = (phase,cache) == (1,'cold')
            control = directory(temp,phase,'965tail' if adjusted else '965measured',cache)
            actual = directory(temp,phase,'966release',cache)
            joint = read(actual/'joint.json')
            assert joint['firmware_SHA256']==firmware and joint['client_SHA256']==client
            for file in ('events.json','packets.jsonl','producer.jsonl','window.csv','seal528.csv'):
                assert sha(actual/file)==sha(control/file),(phase,cache,file)
            outcome = summary(actual,control,map1920_destination=None)
            physical_control = read(directory(temp,phase,'955final',cache)/'verified905.json')
            timing = record[str(phase)]['late_feedback'] if adjusted else case
            assert outcome['six']==case['six']==13 and outcome['D2_before_911_reveal']==case['input_blocks']==17
            assert outcome['ACK912']==timing['ACK912'] and case['exact_prior_addresses'] and case['prior_DMA_B']==496
            assert decode(actual/'records.bin',966)==decode(control/'records.bin',955)
            assert (actual/'records.bin').stat().st_size==8044
            recorder = read(actual/'verified905.json')
            assert recorder['pages']==physical_control['pages']==15 and recorder['selected']==physical_control['selected']==1
            if cache=='cold':
                for name,status in [('bad-seal',224),('stop908',228)]:
                    guard=actual/('guard-'+name)
                    result=read(guard/'result.json')
                    assert result['passed'] and result['commits']==3 and result['last_status']==status
                    assert sha(guard/'retained.rgb')==sha(actual/'frame-907.rgb')
            window = [r for r in rows(actual/'window.csv') if r['g']=='909']
            last_obj = next(r for r in reversed(window) if (r['op'],r['section'],r['event'])==('7','1','load'))
            seal = [r for r in window if r['op']=='3']
            marks = {name:next(r for r in seal if r['event']==name)
                     for name in ('load','upload165_entry','ppu_dma','reveal')}
            chain = [last_obj, *marks.values()]
            times = [int(r['clock']) for r in chain]
            assert times==sorted(times)
            cases[f'{cache}-{phase}'] = dict(VBlanks=13,input_blocks=17,prior_DMA_B=496,matched_RGB=outcome['RGB'],
                final_ACK=outcome['ACK912'],ack_gain_vs964_ms=timing['ACK_gain_vs964_ms'],
                reference955_VBlanks=physical_control['intervals'][1],
                ack_gain_vs955_replay_ms=milliseconds(physical_control['final_ACK'][1]-outcome['ACK912']),
                SPI_trace=sha(actual/'events.json'),trace_B=8044,reveals=outcome['reveals'],
                generation909=dict(last_OBJ_to_SEAL_ms=milliseconds(times[1]-times[0]),
                    SEAL_to_upload_ms=milliseconds(times[2]-times[1]),upload_to_first_DMA_ms=milliseconds(times[3]-times[2]),
                    first_DMA_to_publication_ms=milliseconds(times[4]-times[3]),
                    frame_line={name:[int(r['frame']),int(r['line'])] for name,r in zip(('last_OBJ',*marks),chain)}))
    return cases


def package(temp):
    from package_nes_trial704 import decode as unpack
    from analyze_nes_chr951 import board_cost
    source = ARM/'link/src/obj-nes-100/firmware.stm'
    ref = read(ROOT/'analysis/trial955-package.json')
    validated = read(ROOT/'analysis/mail964-results.json')
    assert sha(source)==validated['firmware']
    data = (WORK/'link/src/obj-nes-100/firmware.stm').read_bytes()
    firmware = digest(data)
    size,crc,inverse = struct.unpack_from('<III',data,8)
    assert data[:4]==b'STM3' and size+512==len(data)<=212992
    assert crc^inverse==0xffffffff and crc==zlib.crc32(data[512:])
    old = source.read_bytes()[512:]
    renamed = old.replace(b'955',b'966')
    differences = [i for i,(a,b) in enumerate(zip(renamed,data[512:],strict=True)) if a!=b]
    pos, = differences
    assert struct.unpack_from('<H',renamed,pos)==(955,) and struct.unpack_from('<H',data,512+pos)==(966,)
    for name in (' 966.nh1','mmc966.nes','fpga_mmc966.bi3','nes-progress-mmc966.txt',
                 'nes-budget-mmc966.txt','nes-game-last-mmc966.txt','nes-frame-mmc966.bin'):
        assert name.encode()+b'\0' in data and name.replace('966','955').encode()+b'\0' not in data
    proof = WORK/'proof'
    windows = read(proof/'windows.json')
    assert windows['firmware_SHA256']==firmware and windows['accepted']==ref['windows']['accepted']
    timer,menu,loader = (read(proof/f'{name}.json') for name in ('timer','menu','loader'))
    assert all(p['firmware']==firmware for p in (timer,menu,loader))
    assert timer['passed'] and menu['rows']['normal']['released'] and loader['cases']==ref['loader']['cases']
    base = read(proof/'base/result.json')
    assert base['passed'] and base['safe_return'] and base['base_restored'] and base['firmware_sha256']==firmware
    assert base['config_paths']==['/sd2snes/fpga_mmc966.bi3','/sd2snes/fpga_base.bi3']
    rx = read(proof/'sram.json')['cases']
    assert len(rx['normal']['d0_sites'])==4 and rx['normal']['checked_retire'] and not rx['bad-crc']['checked_retire']
    identity = read(WORK/'identity950.json')
    assert identity['stale_generation'] and identity['stale_token'] and identity['unexpected_chunk_tested']
    board = temp/'nes-trial816-board964'
    fit = board_cost(board)
    assert fit==validated['board'] and min(fit['slack_ns'].values())>0
    out = temp/'nes-image966-release'
    img = read(out/'image.json')
    bi = (out/'fpga_mmc966.bi3').read_bytes()
    assert img['programmer']['passed'] and digest(bi)==img['BI3']==img['programmer']['image_sha256']
    assert digest(unpack(bi))==img['RBF']==img['programmer']['rbf_sha256']
    assert sha(out/'board.sof')==img['SOF']==fit['reports']['board.sof']
    rom = (PACKED/'sink165.sfc').read_bytes()
    client = digest(rom)
    bus = read(out/'bus/result.json')
    assert bus['program']==sha(board/'sink-program.hex') and bus['bus']==sha(board/'nes_sink_bus165.sv')
    assert bus['client']==client and bus['bytes']==5120
    memory, = (board/'db').glob('board.ram*_nes_sink_bus165_*.hdl.mif')
    cells = sorted((int(i),int(v,2)) for i,v in re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',memory.read_text(),re.M))
    assert [i for i,_ in cells]==list(range(5120))
    assert bytes(v for _,v in cells)==rom[:5056]+rom[-64:]==bytes.fromhex((board/'sink-program.hex').read_text())
    report = dict(edition=966,firmware=firmware,Flash_B=len(data),free_B=212992-len(data),
        physical=False,reference='MMC955',client=client,route=fit,image=img,bus=bus,compiled_MIF=sha(memory),
        timer_pass=True,base_restore=True,menu_return=True,CRC_rejected=True,SRAM_D0_sites=4,
        identity=identity,windows=windows,loader=loader,cases=checked_cases(temp,firmware,client))
    write_verified_archive(WORK,ref,data,bi,report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare','image','guards','replay','consumer','pack'))
    parser.add_argument('--phase',type=int,choices=(1,2))
    parser.add_argument('--cache',choices=('cold','warm'))
    parser.add_argument('path', type=Path, nargs='?')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif not args.path:
        parser.error('image/pack requires the simulation directory, guards requires the game ROM')
    elif args.action == 'image':
        make_image(args.path)
    elif args.action == 'guards':
        guards(args.path)
    elif args.action == 'consumer':
        from nes_tail961 import guards as consumer_guards
        if not args.phase:
            parser.error('consumer requires --phase')
        consumer_guards(args.path,args.phase,'966release')
    elif args.action == 'replay':
        if not args.phase or not args.cache:
            parser.error('replay requires --phase and --cache')
        replay(args.path,args.phase,args.cache)
    else:
        package(args.path)
