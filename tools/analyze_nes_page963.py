"""Compare the same ARM with zero, eight or sixteen early tiles and the 961 control."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_chr951 import board_cost, logtext
from analyze_nes_deadline922 import measure
from analyze_nes_palette921 import coverage
from analyze_nes_tail961 import milliseconds
from check_nes_blank959 import read, rows, sha, summary, directory
from check_nes_menu533 import check
from nes_page963 import ARM, PACKED, WORK


def case(folder, control, checks):
    output = summary(folder, control)
    metrics, observed = measure(folder, ARM)
    overhead = observed['params']['driver_extra_us']
    assert abs(overhead.pop('0xeb')-overhead['0xea']) < 1e-6
    assert observed == checks
    last = metrics['frames'][912]
    pre = coverage([r for r in last['preDMA'] if r[3] == last['VBlank'][3]-1])
    hints = read(folder/'hint963.json')
    fills = Counter(g for g, addr, grant, reply in hints['fills'])
    jobs = [j for j in map(json.loads,(folder/'producer.jsonl').read_text().splitlines())
            if j['generation'] == 912]
    loads = [r for r in rows(folder/'window.csv')
             if r['g']=='912' and r['op']=='7' and r['event']=='load']
    tail = []
    for job, load in zip(jobs,loads,strict=True):
        if job['token'] in (35,36):
            tail.append(dict(token=job['token'],size=job['bytes'],ready=job['producer'],
                             first_E8=job['observed'],load=int(load['clock']),line=int(load['line'])))
    grants = [x for _,addr,_,_,requests in read(folder/'slots930.json')
              if addr==3084*16 for x in requests if x[0]==912]
    assert sha(folder/'client.sfc') == sha(PACKED/'sink165.sfc')
    assert read(folder/'joint.json')['firmware_SHA256'] == sha(ARM/'link/src/obj-nes-100/firmware.stm')
    return dict(six=output['six'],reveals=output['reveals'],ACK912=output['ACK912'],
                input_blocks=output['D2_before_911_reveal'],prior_DMA912_B=len(pre),tail=tail,
                hints=hints['hints'],fills=dict(fills),foreground_3084_row0=grants,
                VRAM_B=output['VRAM_B'],RGB_frames=output['RGB'])


def analyze(temp):
    fw = ARM/'link/src/obj-nes-100/firmware.stm'
    base = read(ARM/'proof/base/result.json')
    menu = check(ARM/'link/src','955')
    assert menu['firmware']==base['firmware_sha256']==sha(fw)
    assert base['safe_return'] and base['base_restored'] and menu['rows']['normal']['released']
    board=temp/'nes-trial816-board963'
    log=logtext(board/'guards963.log')
    assert 'PASS963 SPI CRC' in log and 'Errors: 0' in log
    result=dict(physical_reference='MMC955', flash_B=fw.stat().st_size, flash_limit_B=212992,
                reference_flash_B=(WORK/'link/src/obj-nes-100/firmware.stm').stat().st_size,
                firmware=sha(fw),menu=menu['rows']['normal']['released'],base=base['config_paths'],
                RTL_guard=sha(board/'guards963.log'), board={str(n):board_cost(temp/f'nes-trial816-board{n}') for n in (961,963)},
                cases={})
    for phase in (1,2):
        for cache in ('cold','warm'):
            reference=directory(temp,phase,'961wirepair' if cache=='cold' else '961pair',cache)
            baseline,checks=measure(reference,WORK)
            cases={}
            for variant in (('off','on','both') if cache=='cold' else ('off','both')):
                folder=directory(temp,phase,'963bnes-page963'+variant,cache)
                row=case(folder,reference,checks)
                row['ACK_gain_vs_961_ms']=milliseconds(baseline['final_ACK']-row['ACK912'])
                cases[variant]=row
                if cache=='cold' and variant=='both':
                    for name,status in [('bad-seal',224),('stop908',228)]:
                        guard=folder/('guard-'+name)
                        status_log=read(guard/'result.json')
                        assert status_log['passed'] and status_log['last_status']==status and status_log['commits']==3
                        assert sha(guard/'retained.rgb')==sha(folder/'frame-907.rgb')
                    row['rejected_bad_seal_and_STOP_retained_generation']=907
            assert cases['both']['six']==13 and cases['both']['input_blocks']==17
            assert cases['both']['prior_DMA912_B']==496
            if cache=='cold':
                assert cases['on']['prior_DMA912_B']==176 and cases['off']['six']==14
            cases['both']['ACK_gain_vs_same_ARM_off_ms']=milliseconds(cases['off']['ACK912']-cases['both']['ACK912'])
            result['cases'][f'{cache}-{phase}']=cases
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.write_text(json.dumps(analyze(args.temp),indent=2)+'\n')
