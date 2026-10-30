# SPDX-License-Identifier: MIT
"""Classify received492 pre-receiver boot timeout; never accept it as FPS data."""
import argparse,hashlib,json,re
from pathlib import Path
from analyze_nes_supply485_hardware import fields,analyse
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--compare-roms',type=Path,nargs=4,metavar=('OLD_BOARD','OLD_CLIENT','NEW_BOARD','NEW_CLIENT'))
    a=p.parse_args();assert not a.out.exists()
    paths={k:a.raw/f'nes-{k}-mmc492.txt'for k in ['progress','budget','game-last']}
    raw={k:v.read_text(encoding='utf-8-sig')for k,v in paths.items()};g,b=fields(raw['game-last']),fields(raw['budget'])
    expected={'candidate':'NES-MMC492','board_expected_hex':'7b','board_observed_hex':'7b','verified':'1',
              'loaded_bytes':'393216','compared_bytes':'393216','verify_error':'0','run_passed':'0','run_error':'6',
              'native_frames':'0','native_transactions':'0','native_wire_bytes':'0','trace_commits':'0',
              'stop_ok':'1','base_restored':'1','safe_to_reload':'1','menu_state':'PREPARED_RESET_HELD'}
    for k,v in expected.items():assert g[k]==v,(k,g.get(k))
    assert b['boot_reason']=='5' and b['boot_ticks']=='500' and b['open']=='0'
    rows=[list(map(lambda n:int(n,16),line.split(',')))for line in re.findall(r'^b\d+=(.*)$',raw['budget'],re.M)]
    assert len(rows)==12 and all(not any(row)for row in rows)
    try:analyse(a.raw,492)
    except AssertionError:pass
    else:raise AssertionError('Boot failure incorrectly accepted as performance run')
    marks={stage:int(ms)for stage,ms in re.findall(r'stage=(\S+).*?elapsed_ms=(\d+)',raw['progress'])}
    r={'trial':492,'hardware_run_passed':False,'failure_class':'SNES_boot_ready_timeout_before_receiver',
       'user_report':{'execution_failed':True,'menu_return_normal':True},
       'ROM_load_CRC_readback_passed':True,'loaded_payload_B':393216,
       'display_attempt_ms':marks['DISPLAY_STOPPED']-marks['DISPLAY_NEXT'],
       'boot_wait_ms':int(b['boot_ticks'])*int(b['tick_ms']),'boot_polls':int(b['boot_polls']),
       'boot_first_hex':b['boot_first_hex'],'boot_last_hex':b['boot_last_hex'],
       'boot_stage_observed':int(g['screen_stage']),'screen_telemetry_trusted':False,
       'native_transactions':0,'completed_displays':0,'physical_FPS':None,
       'phase_counters_opened':False,'all12_buckets_zero':True,'STOP_base_recovery_passed':True,
       'strict_performance_parser_rejects_failed_run':True,
       'source_files':{q.name:{'bytes':q.stat().st_size,'SHA256':hashlib.sha256(q.read_bytes()).hexdigest()}for q in paths.values()},
       'cause_proven':False,'limits':['Ready not observed does not identify CPU PC or prove no CPU instruction executed',
                                      'No speed comparison:actual receive/plan/SEAL not entered',
                                      'Sampled bus flags and stage0 do not distinguish corrupted reads,missed milestone or bootstrap failure'],
       'decision':'Withdraw492 hardware selection;freeze new FPGA/SNES candidate;isolate with byte-identical known-good489 FPGA and retained491 ARM query changes;do not bypass boot gate',
       'next':'493 physical boot/three logs/menu confirmation;root cause remains open'}
    if a.compare_roms:
        checked=[]
        for board,client in [a.compare_roms[:2],a.compare_roms[2:]]:
            m=next((board/'db').glob('*.mif'));pairs={int(i):int(b,2)for i,b in re.findall(r'(\d+)\s*:\s*([01]+)\s*;',m.read_text())}
            image=bytes(pairs[i]for i in range(5120));expected=bytes.fromhex((client/'sink-program.hex').read_text());assert image==expected
            checked.append({'bytes':len(image),'generated_MIF_matches_ROM':True,'ROM_SHA256':hashlib.sha256(image).hexdigest()})
        r['logical_ROM_comparison']=checked;r['logical_ROM_comparison_is_not_hardware_readback']=True
    a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({'failure':r['failure_class'],'wait_ms':r['boot_wait_ms'],'FPS':None,'recovery':True}))
