"""Reconcile pinned MMC690 replay costs and existing long-session guard limits.

This re-analyzes prior actual linked ARM/65816 executions with modeled bus/ROM
timing. It neither runs new firmware nor partitions the physical 25.56ms mean.
"""
import argparse
import json
from pathlib import Path
from analyze_nes_output664 import trace, read, sha
from nes_schedule492 import funcs

ROOT=Path(__file__).resolve().parents[1]

def analyze(a):
    proof=read(ROOT/'analysis/status689-verification.json')
    old=funcs(a.old_arm/'obj-nes-100/sd2snes.elf')
    current=funcs(a.arm/'obj-nes-100/sd2snes.elf')
    assert old==current and len(current)==799
    assert sha(a.arm/'obj-nes-100/firmware.stm')=='71e4f00670d26599872c2c294e2f5f8c793a4b2b5aacc2b22e53425e44f7ea5d'
    phases={}
    for phase in (1,2):
        folder=a.traces/f'nes-status689-arm{phase}'
        pins=proof['phases'][str(phase)]['candidate']['pins']
        for name,h in pins.items():assert sha(folder/name)==h,name
        assert read(folder/'joint.json')['firmware_SHA256']==sha(a.old_arm/'obj-nes-100/firmware.stm')
        t=trace(folder,a.traces/f'nes-front638-both{phase}h')
        assert t['checked']['rows'][951]['line']<=246
        assert t['intervals'][952]['VBlank']==3 and t['intervals'][957]['final_waits']==0
        assert all(abs(sum(f['terms'].values())-f['total_ms'])<1e-8 for f in t['frames'].values())
        assert t['dense']['terms']['last_blank_wait']==0
        # An optimistic deletion bound, NOT a runnable DMA/schedule candidate.
        ceilings={g:dict(last_tile_to_SEAL_load_ms=d['last_tile_to_SEAL_load_ms'],
                        post_SEAL_upload_wait_ms=d['terms']['upload_wait'],
                        post_SEAL_active_DMA_ms=d['terms']['DMA'])
                  for g,d in t['details'].items()}
        phases[phase]=dict(all_warm=t['all_warm'],dense=t['dense'],
            work={g:f['work'] for g,f in t['frames'].items()},
            frame_costs=t['frames'],intervals=t['intervals'],early_DMA_B=t['early_DMA_B'],
            details=t['details'],diagnostic_bounds=ceilings,
            last_ACK=t['checked']['last_ACK'],
            pins={name:sha(folder/name) for name in (*pins,'seal528.csv','tile532.csv')})
    assert phases[1]['work']==phases[2]['work']
    guards=read(a.guards)
    assert guards['passed'] and len(guards['cases'])==7
    assert guards['firmware']==sha(a.arm/'obj-nes-100/firmware.stm')
    sources=('nes_native_runtime165.c','nes_native_runtime165.h','nes_runtime_board165.inc',
             'nes_budget210.c','nes_budget210.h','nes_cf86_session094.c')
    return dict(stage=692,scope=__doc__,baseline='MMC690',control='MMC666',
        merged_PR155='c5a25a448e856ce9eddeb86d90965d2ae804a966',
        same_linked_functions=799,firmware=guards['firmware'],phases=phases,
        existing_guard_tests=guards,source_pins={n:sha(a.arm/n) for n in sources},
        unchanged_budget=dict(Flash_B=212984,Flash_free_B=8,static_data_B=10040,BSS_B=19544,
            LE=15295,LAB=963,LAB_free=0,M9K=56,M9K_free=0,CPU_body_free_B=0,CPU_packed_free_B=13),
        source_audit=dict(play_limit_ticks=6000,tick_ms=10,cumulative_step_limit=4194304,
            zero_limit_is_unlimited=False,post55s_bin='all later frame-start samples collapse into bin11',
            physical_reset_is_normal_user_exit=False,
            required_changes=['explicit long-play mode','progress-based bounded stall detection',
                'checked live user-stop request distinct from hardware fault',
                'bounded long-session statistics and explicit elapsed duration',
                'generation/credit wrap, partial input, STOP and final ACK ownership tests']),
        new_target_implementation=False,new_FIT_STA=False,new_hardware_measurement=False,
        unlimited_build_delivered=False,
        evidence={n:sha(ROOT/'analysis'/n) for n in ('status689-verification.json','trial690-package.json','hardware691-mmc690.json')},
        tools={n:sha(ROOT/'tools'/n) for n in ('analyze_nes_output692.py','check_nes_longrun692.py')})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','old-arm','traces','guards','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=analyze(a);a.out.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('PASS692: 104 warm cost sums, 2 starts, 799 identical functions, 7 existing guard boundaries')
