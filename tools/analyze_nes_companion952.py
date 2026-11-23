"""Reconcile per-generation row contents, actual grant clocks, and linked 912 DMA timing."""
import csv
import json
import re
import sys
from pathlib import Path

from analyze_nes_chr951 import ROOT, RELEASE, ROM, MASTER, Calendar, board_cost, coverage, directory, inspect, logtext, port_log, read, sha, timing
from nes_companion952 import project


def preceding(metrics):
    blank=metrics['stages'][912]['frame']-1
    return [entry for entry in metrics['preDMA'] if entry[-1]==blank]


def port(folder,g,variant,chr_bytes):
    path=folder if g==912 else folder/f'gen{g}'
    log=path/f'port952-{variant}.log'
    if not log.exists():
        return None
    text=logtext(log)
    result=port_log(log)
    if g==912:
        polls=[list(map(int,line.split())) for line in (path/'polls914.txt').read_text().splitlines()]
        result['first_consuming_poll']=[
            [token,count,ready,next(p[0] for p in polls if p[3]==token)]
            for token,count,ready in result['published'] if any(p[3]==token for p in polls)]
    grants=set(map(int,(path/'grants914.txt').read_text().split()))
    aux=[(int(at),int(a)) for at,a in re.findall(r'AUX952 at=(\d+) address=(\d+)',text)]
    hits=[int(a) for a in re.findall(r'HIT952 at=\d+ address=(\d+)',text)]
    target={16*tag+row for tag in (6244,6245) for row in range(8)}
    result.update(aux_pairs=len(aux),target_aux=[r for r in aux if r[1] in target],
                  target_hit_addresses=sorted(target.intersection(hits)),
                  aux_outside_grants=[at for at,_ in aux if at not in grants])
    rows=path/'rows-out951.hex'
    if not rows.exists() or result['error']:
        return result
    data=[line.strip() for line in rows.read_text().splitlines() if line.strip() and not line.startswith('//')]
    assert len(data)==256
    retained=[]
    for a in sorted(target):
        tag=a//16
        slot=(tag>>10&1)*16+((tag&15)^((tag>>8&1)<<1))
        word=data[8*slot+a%16]
        expected=(1<<25)|((tag>>4)<<16)|(chr_bytes[a+8]<<8)|chr_bytes[a]
        if 'x' not in word.lower() and int(word,16)==expected:
            retained.append(a)
    result.update(retained_pairs=len(retained),snapshot=sha(rows))
    return result


def analyze(temp):
    ref=read(ROOT/'analysis/header950-results.json')['cases']
    calendar=Calendar(temp/'nes-service509-rom03')
    safety=read(RELEASE/'safety950.json')
    assert safety['CRC_rejected'] and safety['SRAM_D0_sites']==4 and safety['menu']
    assert safety['firmware']==sha(RELEASE/'link/src/obj-nes-100/firmware.stm') and safety['consumer']==sha(ROM/'sink165.sfc')
    assert read(RELEASE/'proof/base/result.json')['base_restored']
    proof=temp/'nes-safety952'/'proof'
    menu=read(proof/'menu.json')
    assert menu['firmware']==safety['firmware'] and menu['rows']['normal']['released']
    assert read(proof/'base/result.json')['base_restored'] and read(proof/'timer.json')['passed']
    loader=read(proof/'loader.json')['cases']
    assert loader['original']['program'] and not loader['damaged']['program']
    assert read(proof/'sram.json')['cases']['normal']['checked_retire']
    assert read(proof.parent/'consumer952.json')==safety['STOP']
    guard_files=list(proof.rglob('*.json'))+[proof.parent/'consumer952.json']
    result=dict(physical=False,master_Hz=MASTER,safety=safety,
                rerun_safety={p.relative_to(proof.parent).as_posix():sha(p) for p in guard_files},variants={})
    for v in ('pair','halves','checked','checkedrows'):
        hardware='checked' if v=='checkedrows' else v
        folder=project(temp,hardware)
        board=board_cost(folder)
        data=result['variants'][v]=dict(board=board,cases={},
            board_source_sha256={name:sha(folder/name) for name in ('nes_e9_rows914.sv','nes_source_tile192.sv','sink-program.hex')})
        for guard,marker in [('guards951','PASS914 checked'),('row951','PASS951 lease'),('row952','PASS952 16 actual')]:
            path=folder/f'{guard}.log'
            if path.exists():
                data[guard]=dict(passed=marker in logtext(path),sha256=sha(path))
        for cache in ('warm','cold'):
            for phase in (1,2):
                case=cache+str(phase)
                path=directory(temp,phase,'952'+v,cache)
                m,q=inspect(path,RELEASE,calendar)
                baseline='951bankedrows' if v=='checkedrows' else '951banked'
                base,expected=inspect(directory(temp,phase,baseline,cache),RELEASE,calendar)
                assert all(q[k]==expected[k] for k in ('map','colors','RGB','sections','tiles'))
                target,_=inspect(directory(temp,phase,'950bound',cache),RELEASE.parent/'bound',calendar)
                dma=preceding(m)
                same=coverage(dma).keys()==coverage(preceding(target)).keys()
                margin=ref[case]['bound']['final_D2']+ref[case]['bound']['capture_line_margin']-m['capture_D2']
                gain=ref[case]['bound']['final_ACK']+ref[case]['bound']['ACK_advance_vs935']-m['final_ACK']
                blocks=timing(path)['returned_before_show']
                aux=read(path/'companion952.json')
                wanted={16*t+r for t in (6244,6245) for r in range(8)}
                chr_bytes=bytes.fromhex((path/'chr914.hex').read_text()) if (path/'chr914.hex').exists() else None
                actual={}
                for g in range(905,913):
                    r=port(path,g,hardware,chr_bytes)
                    if r:
                        actual[g]=r
                with (path/'window.csv').open() as f:
                    transfers=[r for r in csv.DictReader(f) if r['g']=='912' and r['event'] in ('ppu_dma','ppu_last')
                               and int(r['clock'])<m['stages'][912]['SEAL']]
                dma_lines=[]
                for job,start,end in zip(m['preDMA'],transfers[::2],transfers[1::2],strict=True):
                    if job in dma:
                        dma_lines.append(dict(address=job[1],size=job[2],vblank=job[3],
                            start_clock=int(start['clock']),end_clock=int(end['clock']),
                            start_line=int(start['line']),end_line=int(end['line'])))
                measured=[909,912] if cache=='warm' else list(range(905,913))
                matched=lambda g:g in actual and actual[g]['polls'] and actual[g]['polls'][1]==0
                all_polls=all(matched(g) for g in measured)
                target_rtl=None
                if cache=='cold' and all(g in actual and 'retained_pairs' in actual[g] for g in range(908,913)):
                    target_rtl=(set(a for _,a in actual[908]['target_aux'])==wanted and
                                all(actual[g]['retained_pairs']==16 for g in range(908,913)) and
                                not any(actual[g]['target_aux'] for g in (909,910,911)) and
                                set(actual[912]['target_hit_addresses'])==wanted and bool(matched(912)) and
                                all(not r['aux_outside_grants'] and not r['error'] for r in actual.values()))
                linked=(blocks==17 and margin>=0 and same and m['prior_blank_B']==496 and m['tail_grant'] and
                        m['total']==(13 if cache=='warm' else 14) and gain>0)
                data['cases'][case]=dict(linked_target=linked,blocks=blocks,capture911_margin_us=round(margin*1e6/MASTER,3),
                    preceding_DMA=dma,transfer_lines=dma_lines,baseline=baseline,baseline_preDMA=base['prior_blank_B'],
                    all_RTL_E8_equal=all_polls,retention_and_912_E8=target_rtl,same_coverage=same,paired_tail_grant=m['tail_grant'],intervals=m['total'],gaps=m['gaps'],
                    prior_B=m['prior_blank_B'],final_ACK=m['final_ACK'],gain_vs935_ms=round(gain*1000/MASTER,6),
                    gain_vs951_ms=round((base['final_ACK']-m['final_ACK'])*1000/MASTER,6),
                    grants908=[[a,gr,done] for g,a,gr,done in aux if g==908 and a in wanted],
                    later_refreshes=sum(908<g<912 and a in wanted for g,a,_,_ in aux),rtl=actual,joint_sha256=sha(path/'joint.json'))
    selected=result['variants']['checkedrows']
    cases=selected['cases']
    result['verified']={
        'linked_four_conditions':all(r['linked_target'] for r in cases.values()),
        'whole_board_fit_sta':selected['board']['fit'] and min(selected['board']['slack_ns'].values())>0,
        'two_cold_phases_physical_retention_and_912_polls':all(cases[c]['retention_and_912_E8'] for c in ('cold1','cold2')),
        'all_sampled_E8_all_cases':all(r['all_RTL_E8_equal'] for r in cases.values()),
        'actual_port_guards':all(selected[g]['passed'] for g in ('guards951','row951','row952'))}
    return result


if __name__=='__main__':
    result=analyze(Path(sys.argv[1]))
    (ROOT/'analysis/companion952-results.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    for v,data in result['variants'].items():
        print(v,[(k,r['prior_B'],r['intervals'],r['capture911_margin_us'],r['gain_vs935_ms'],r['linked_target']) for k,r in data['cases'].items()])
