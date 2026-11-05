"""Bind same-cycle OE/CE replacement, unchanged schedules and routed board costs."""
import argparse,csv,json,re
from pathlib import Path
from budget_nes_board611 import fit,timing
from check_nes_wire600 import ROOT,read,sha
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('board','first','simulation','boundary','schedule','firmware','client','report'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=read(ROOT/'analysis/board611-verification.json');inputs=read(a.board/'inputs612.json')
    for n,h in inputs.items():assert sha(a.board/n)==h
    changed=[n for n,h in prior['inputs'].items() if inputs[n]!=h]
    assert set(changed)=={'nes_rom_physical.sv','board.sdc'}
    miter=read(a.simulation/'result.json');boundary=read(a.boundary/'result.json')
    assert miter['reference']==prior['inputs']['nes_rom_physical.sv']
    assert miter['candidate']==inputs['nes_rom_physical.sv']==boundary['inputs']['nes_rom_physical.sv']
    assert miter['bench']==sha(ROOT/'tools/nes_oe612_tb.sv') and miter['log']==sha(a.simulation/'vsim.log')
    assert boundary['wiring']==inputs['nes_live_joint.sv']
    for n,h in boundary['inputs'].items():assert inputs[n]==h
    schedule=read(a.schedule);assert schedule['phases']==prior['phases'] and schedule['schedule_gate']
    assert sha(a.firmware)==prior['firmware_SHA'] and a.firmware.stat().st_size==212992
    assert sha(a.client)==prior['client_SHA']
    phases=[]
    for q in schedule['phases']:
        c=q['candidate'];assert c['cache']['BG_hit']==48 and c['cache']['OBJ_capture']==1200 and c['watched']['957']['final_waits']==0
        phases.append(dict(phase=q['phase'],dense_ms=c['dense_ms'],dense_VB=c['dense_VB'],last_ACK=c['last_ACK'],
            watched=c['watched'],delta_vs611_ms=0,delta_vs_fair_reference_ms=q['last_ACK_delta_ms'],cache=c['cache']))
    sta=timing(a.board,'paths612.tsv')
    with (a.board/'io612.tsv').open() as f:io=list(csv.DictReader(f,delimiter='\t'))
    assert len(io)==9 and all(r['from'].endswith('reading_active') or '|chip_active[' in r['from'] for r in io)
    rpt=(a.board/'output_files/board.map.rpt').read_text()
    first=(a.first/'output_files/board.fit.rpt').read_text()
    assert '964 LABs' in first
    result=dict(stage=612,inputs=inputs,changed=changed,fit=fit(a.board),baseline_fit=prior['board'],STA=sta,
        baseline_STA=prior['reviewed_STA'],pin_paths=io,IO_budget_ns=12,
        miter=miter,boundary=boundary,phases=phases,schedule_recheck_SHA=sha(a.schedule),
        schedule_method='Revalidated existing four actual ARM/65816 traces; same binaries/cache and cycle-identical reader tests. No new full ARM timeline run; no new FPS gain.',
        first_attempt=dict(scope='OE mask removal only',fit=False,required_LAB=964,available_LAB=963,report=sha(a.first/'output_files/board.fit.rpt')),
        reader_FSM_extracted='State Machine - |fxpak_nes_screen137_top|nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|state' in rpt,
        ARM_Flash_B=212992,ARM_SHA=sha(a.firmware),client_SHA=sha(a.client),ARM_Flash_free_B=0,M9K_free=56-fit(a.board)['M9K'],
        whole_STA_passed=all(float(v['slack'])>=0 for v in sta['worst'].values()),physical=False,
        hardware_package=False,physical_baseline='MMC577')
    a.report.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
