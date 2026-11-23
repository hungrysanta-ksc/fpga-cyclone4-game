"""Build the 60-second Adventure Island IV release from the checked 950/952 pair."""
import argparse
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from analyze_nes_chr951 import ROOT, RELEASE, ROM, read, sha
from nes_companion952 import project
from package_nes_trial704 import image
from prepare_nes_frame900 import QUARTUS
from prepare_nes_trial802 import rename_edition

WORK = ROOT.parent/'probes/nes-trial955'


def prepare():
    ref = read(ROOT/'analysis/admission954-results.json')
    assert sha(RELEASE/'link/src/obj-nes-100/firmware.stm') == ref['firmware']
    assert sha(ROM/'sink165.sfc') == ref['consumer']
    shutil.copytree(RELEASE/'link',WORK/'link')
    src = WORK/'link/src'
    rename_edition(src,WORK/'markers',950,955)
    for file in (WORK/'markers').iterdir():
        shutil.copyfile(file,src/file.name)
    p = src/'nes_budget210.c'
    original = p.read_bytes()
    assert original.count(b'log900p->edition=950;') == 1
    p.write_bytes(original.replace(b'log900p->edition=950;',b'log900p->edition=955;'))


def routed_image(temp):
    board = project(temp,'checked')
    assert sha(board/'output_files/board.sof') == read(ROOT/'analysis/admission954-results.json')['board_sof']
    image(SimpleNamespace(board=board,quartus=QUARTUS,out=temp/'nes-image955',number='955'))


def guards():
    from check_nes_supply905_arm import run
    from nes_order938 import empty_next_offer
    import check_nes_header950 as header
    run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',
        WORK,955,short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
    with patch.object(header,'work',lambda _:WORK):
        header.test('release')


def final_cases(temp, firmware, consumer):
    from analyze_nes_chr951 import directory
    from read_nes_supply905 import decode

    reference = read(ROOT/'analysis/feedback953-results.json')['cases']
    fixtures = ('wire914.hex','batch914.txt','tokens914.txt','polls914.txt','sizes914.txt',
                'cap914.txt','chr914.hex','expected914.hex','grants914.txt','origin914.txt')
    cases = {}
    for key, ref in reference.items():
        phase, cache = int(key[-1]), key[:-1]
        linked = directory(temp, phase, '955final', cache)
        prior = directory(temp, phase, '953combined' if key=='cold2' else '953feedback', cache)
        control = directory(temp, phase, '925final', cache)
        joint = read(linked/'joint.json')
        assert joint['passed'] and joint['last_status']==1
        assert (joint['firmware_SHA256'],joint['client_SHA256'])==(firmware,consumer)
        traces = ('events.json','packets.jsonl','window.csv','seal528.csv',
                  *(f'frame-{g}.rgb' for g in range(905,913)))
        for name in traces:
            assert sha(linked/name)==sha(prior/name), (key,name)
        polls = 0
        for generation, rtl in ref['rtl'].items():
            old, new = (p if generation=='912' else p/('gen'+generation) for p in (prior,linked))
            for name in fixtures:
                assert sha(old/name)==sha(new/name), (key,generation,name)
            assert sha(old/'port952-checked.log')==rtl['log'] and rtl['polls'][1]==0
            polls += rtl['polls'][0]
        result = read(linked/'verified905.json')
        assert result==read(prior/'verified905.json')
        assert result['final_ACK'][1]==ref['ack'] and result['intervals'][1]==ref['intervals']
        assert ref['linked_pass'] and ref['blocks']==17 and ref['prior_DMA']==496
        assert ref['margin_us']>0 and ref['gain_vs935_ms']>0
        measurements = []
        for path, edition in ((linked,955),(control,925)):
            trace = decode(path/'records.bin',edition)
            assert trace['mode']==0 and trace['dropped']==[0,0]
            assert all('invalid' not in r for r in trace['rows'])
            workload = [(r['generation'],r['BG'],r['OBJ'],r['map']) for r in trace['rows']]
            measurements.append((workload,trace['selected'],read(path/'verified905.json')['pages'],
                                 (path/'records.bin').stat().st_size))
        assert measurements[0]==measurements[1], key
        workload,selected,pages,size=measurements[0]
        assert (len(workload),selected,pages,size)==(6,1,15,8044)
        cases[key] = dict(intervals=ref['intervals'],last_ACK=ref['ack'],advance_vs935_ms=ref['gain_vs935_ms'],
                          DMA_B=ref['prior_DMA'],blocks=ref['blocks'],capture_margin_us=ref['margin_us'],
                          matched_RTL_poll_samples=polls,joint=sha(linked/'joint.json'),diagnostic_pages=pages,
                          matched_MMC925_workload=workload,selected_detail_index=selected,trace_B=size)
    return cases


def package(temp):
    import re
    import struct
    import zlib
    from analyze_nes_chr951 import board_cost
    from package_nes_trial704 import digest, decode as unpack
    from package_nes_trial872 import write_verified_archive

    ref = read(ROOT/'analysis/trial925-package.json')
    fw = (WORK/'link/src/obj-nes-100/firmware.stm').read_bytes()
    n,crc,inverse = struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and n+512==len(fw)<=212992
    assert crc^inverse==0xffffffff and crc==zlib.crc32(fw[512:])
    for name in (' 955.nh1','mmc955.nes','fpga_mmc955.bi3','nes-progress-mmc955.txt',
                 'nes-budget-mmc955.txt','nes-game-last-mmc955.txt','nes-frame-mmc955.bin'):
        assert name.encode()+b'\0' in fw and name.replace('955','950').encode()+b'\0' not in fw
    # The 950 payload changes only at edition strings and the 16-bit trace edition.
    source = (RELEASE/'link/src/obj-nes-100/firmware.stm').read_bytes()
    assert digest(source)==read(ROOT/'analysis/admission954-results.json')['firmware']
    renamed = source[512:].replace(b'950',b'955')
    changed = [i for i,(a,b) in enumerate(zip(renamed,fw[512:])) if a!=b]
    i, = changed
    assert len(source)==len(fw) and renamed[i:i+2]==struct.pack('<H',950)
    assert fw[512+i:514+i]==struct.pack('<H',955)
    arm = digest(fw)
    proof = read(WORK/'safety955.json')
    rom = (ROM/'sink165.sfc').read_bytes()
    assert proof['firmware']==arm and proof['consumer']==digest(rom)
    assert proof['CRC_rejected'] and proof['menu'] and proof['SRAM_D0_sites']==4
    identity = read(WORK/'identity950.json')
    assert identity['stale_generation'] and identity['stale_token'] and identity['unexpected_chunk_tested']
    base = read(WORK/'proof/base/result.json')
    assert base['firmware_sha256']==arm and base['passed'] and base['base_restored'] and base['safe_return']
    assert base['config_paths']==['/sd2snes/fpga_mmc955.bi3','/sd2snes/fpga_base.bi3']
    windows = read(WORK/'proof/windows.json')
    assert windows['firmware_SHA256']==arm and windows['unfinished_excluded']
    assert [(w['start_s'],w['end_s']) for w in windows['accepted']]==[(1,30),(30,60)]
    loader = read(WORK/'proof/loader.json')
    assert loader['firmware']==arm and loader['cases']['original']['program']
    assert not loader['cases']['damaged']['program']
    board = project(temp,'checked')
    out = temp/'nes-image955'
    fit = board_cost(board)
    assert fit==read(ROOT/'analysis/companion952-results.json')['variants']['checkedrows']['board']
    image_info = read(out/'image.json')
    data = (out/'fpga_mmc955.bi3').read_bytes()
    assert sha(out/'board.sof')==fit['reports']['board.sof']==image_info['SOF']
    assert image_info['programmer']['passed'] and digest(data)==image_info['BI3']==image_info['programmer']['image_sha256']
    assert digest(unpack(data))==image_info['RBF']==image_info['programmer']['rbf_sha256']
    bus = read(out/'bus/result.json')
    program = bytes.fromhex((board/'sink-program.hex').read_text())
    assert bus['program']==sha(board/'sink-program.hex') and bus['bus']==sha(board/'nes_sink_bus165.sv')
    assert bus['client']==digest(rom) and len(program)==bus['bytes']==5120 and program==rom[:5056]+rom[-64:]
    mif, = (board/'db').glob('board.ram*_nes_sink_bus165_*.hdl.mif')
    cells = sorted((int(i),int(v,2)) for i,v in re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',mif.read_text(),re.M))
    assert [i for i,_ in cells]==list(range(5120)) and bytes(v for _,v in cells)==program
    report = dict(edition=955,firmware=arm,Flash_B=len(fw),free_B=212992-len(fw),client=digest(rom),
                  physical=False,route=fit,image=image_info,bus=bus,compiled_MIF=sha(mif),proof=proof,
                  identity=identity,base_paths=base['config_paths'],loader=loader,windows=windows,
                  cases=final_cases(temp,arm,digest(rom)))
    write_verified_archive(WORK,ref,fw,data,report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','image','guards','replay','consumer','package'))
    parser.add_argument('temp',type=Path)
    parser.add_argument('--phase',type=int,choices=(1,2))
    parser.add_argument('--cache',choices=('warm','cold'))
    args = parser.parse_args()
    if args.action=='prepare':
        prepare()
    elif args.action=='image':
        routed_image(args.temp)
    elif args.action=='guards':
        guards()
    elif args.action=='replay':
        from nes_feedback953 import BASE, run
        if not args.phase or not args.cache:
            parser.error('replay requires --phase and --cache')
        sources = [BASE]
        if args.phase == 2 and args.cache == 'cold':
            sources.append('953feedback')
        run(args.temp,args.phase,args.cache,sources,'955final',work_arm=WORK,edition=955)
    elif args.action=='consumer':
        from nes_return920 import guards as check_consumer
        import nes_return920
        from nes_deadline947 import check_obj_recovery
        with patch.object(nes_return920,'client',lambda _:ROM):
            check_consumer(args.temp,'first',tag='955final',destination=WORK/'final-guards.json')
        check_obj_recovery(args.temp,'final',work=lambda _:WORK,prefix='955')
    else:
        package(args.temp)
