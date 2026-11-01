# SPDX-License-Identifier: MIT
"""Gate the exact labeled trial on firmware size, command traces, VBlank, STOP and base recovery."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_map526 import ROOT, Calendar, ms, read, run_cost, sha, tiles
from analyze_nes_transfer512 import fpga
from nes_schedule492 import funcs
from check_nes_supply485_arm import ARM


def analyze(a):
    prior=read(ROOT/'analysis/quiet528-verification.json')
    prev527=read(ROOT/'analysis/map527-verification.json')
    older=read(ROOT/'analysis/map526-verification.json')
    reference=read(ROOT/'analysis/prefix523-verification.json')
    obj=a.arm/'obj-nes-100'
    oldobj=a.base_arm/'obj-nes-100'
    fw=obj/'firmware.stm'
    digest=sha(fw)
    assert sha(oldobj/'firmware.stm')==prior['firmware_SHA256']
    saved=prior['Flash_B']-fw.stat().st_size
    assert saved>=500 and fw.stat().st_size<=0x34000
    # Relinking moves absolute addresses. Compare every linked function name and size.
    def sizes(path):
        return Counter((name,size) for name,addr,size in funcs(path/'sd2snes.elf'))
    before,after=sizes(oldobj),sizes(obj)
    removed=before-after
    assert not (after-before)
    assert removed==Counter({('nes_mcu_load_probe',912):1,('nes_rom_spi_command',206):1,('nes_rom_spi_query',126):1})
    assert {'nes_rom_verify','nes_rom_verified_start','nes_menu_sd_probe'}<={n for n,_ in after}
    marker=ARM(a.arm,'normal')
    for path,accepted in ((b'NES MMC3 529.nh1',1),(b'/folder/NES MMC3 529.nh1',1),
                          (b'NES MMC3 524.nh1',0),(b'NES MMC3 529.nes',0)):
        marker.u.mem_write(marker.q,path+b'\0')
        assert marker.call('nes_menu_diagnostic_marker',[marker.q])==accepted
    client=sha(a.client/'sink165.sfc')
    board=fpga(a.board)
    board_ref=older['builds']['row254']
    assert board==board_ref['board']
    assert sha(a.board/'sink-program.hex')==sha(a.client/'sink-program.hex')
    assert sha(a.board/'output_files/board.sof')==board_ref['SOF']==prior['unchanged_SOF']
    guards=read(a.checks/'guard.json')
    assert guards['firmware']==digest and guards['rows']==prior['guards']['rows']
    map_guards=read(a.checks/'mapguards.json')
    assert map_guards['sha256']==digest and map_guards['rows']==prev527['guards'][1]['rows']
    responses=read(a.checks/'responses/result.json')
    assert responses['passed'] and responses['candidate_SHA256']==digest and responses['cases']==40
    window=read(a.checks/'windows.json')
    assert window['firmware_SHA256']==digest and [r['displays'] for r in window['accepted']]==[2,2]
    recovery={}
    for fault in ('none','program','done','busy','token'):
        r=read(a.checks/f'recovery-{fault}/result.json')
        assert r['passed'] and r['firmware_sha256']==digest
        assert r['safe_return']==r['base_restored']==int(fault=='none')
        recovery[fault]=r['safe_return']
    priority=read(a.priority/'priority.json')
    assert {(r['generation'],r['case']) for r in priority}=={(g,k) for g in (906,907) for k in
          ('head','stop','both','late_head','late_stop','bad_manifest','cold','duplicate_map')}
    edges=read(a.priority/'edges.json')
    assert [(r['command'],r['sample_line'],r['size']) for r in edges]==[
            ('map',254,64),('map',255,0),('map',256,0),('tile',233,0)]
    empty=read(a.priority/'empty.json')
    assert empty['size']==64 and empty['commits']==2
    oracle=tiles(a.fixture,957)
    plans={r['generation']:r for r in read(ROOT/'analysis/obj518-verification.json')['plans']['frames']}
    phases=[]
    for i,(base,new,replay) in enumerate(zip(a.base,a.new,a.replay)):
        old=prior['phases'][i]
        s,_=run_cost(new,'row254',dict(reference['phases'][i]['candidate'],firmware=digest),plans,Calendar(a.calendar),oracle)
        assert not (new/'callback-error.txt').exists() and s['client']==old['cost']['client']==client
        for file in ('window.csv','packets.jsonl','obj-phases.json'):
            assert sha(new/file)==sha(base/file)==old['cost']['pins'][file]
        audit=read(replay/'audit.json')
        assert audit['frames']==53 and audit['trace']==s['pins']['window.csv']
        assert sha(replay/'seal528.csv')==sha(new/'seal528.csv')==sha(base/'seal528.csv')
        assert all(sha(base/f'frame-{g}.rgb')==sha(new/f'frame-{g}.rgb') for g in range(905,958))
        for key in ('final_ack','warm_ms','dense_ms','instructions','irqs','SPI_B','ROM_reads','max_banks','dma_B'):
            assert old['cost'][key]==s[key],key
        targets={}
        for g in (952,954):
            f=s['frames'][g-905]
            assert json.loads(json.dumps(f))==old['targets'][str(g)]['candidate_frame'] and f['final_waits']==1
            assert f['display_VBlanks']==prev527['phases'][i]['variants']['frontier']['frames'][g-951]['display_VBlanks']-1
            targets[g]=dict(gap_ms=f['gap_ms'],VBlanks=f['display_VBlanks'],ACK=f['ack'],final_waits=f['final_waits'])
        s.pop('frames')
        phases.append(dict(start=old['start'],targets=targets,cost=s,replay=audit,
                           ACK_vs527_ms=ms(s['final_ack']-prev527['phases'][i]['variants']['frontier']['final_ack']),
                           ACK_vs524_ms=ms(s['final_ack']-older['phases'][i]['variants']['524']['final_ack'])))
    assert [p['start'] for p in phases]==[3000000,3178684]
    return dict(candidate='MMC529',firmware_SHA256=digest,baseline_SHA256=prior['firmware_SHA256'],
                Flash_B=fw.stat().st_size,saved_B=saved,Flash_free_B=0x34000-fw.stat().st_size,BSS_B=window['BSS_B'],
                removed=dict(removed.keys()),retained_functions=sum(after.values()),board=board,SOF=board_ref['SOF'],
                phases=phases,priority=priority,edges=edges,empty=empty,map_guard_cases=len(map_guards['rows']),
                END_guard_cases=len(guards['rows']),response_cases=40,base_return=recovery,windows=window['accepted'],
                hardware_test_pending=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','new','replay'):
        p.add_argument('--'+n,nargs=2,type=Path,required=True)
    for n in ('arm','base-arm','board','client','checks','priority','fixture','calendar','out'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',encoding='utf8',newline='\n')
