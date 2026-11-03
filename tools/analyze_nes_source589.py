# SPDX-License-Identifier: MIT
"""Publish numeric589 evidence only; raw captures/SPI and build logs stay private."""
import argparse,hashlib,json,re,statistics,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def analyze(a):
    result=json.loads((a.test/'result.json').read_text());assert result['passed'] and result['frames']==53 and result['guards']==8
    maps=json.loads((a.map/'result.json').read_text());assert maps['passed']
    assert 'nes_native_export203 #(.MAX_CYCLES(33554432)) source' in (a.map/'reference/nes_region589.sv').read_text()
    fields={'LE':'Total logic elements','comb':'Total combinational functions','FF':'Dedicated logic registers','RAM_bits':'Total memory bits'}
    costs={};hierarchy={};machines={};pins={};warnings={}
    for side in ('reference','candidate'):
        d=a.map/side;summary=(d/'output_files/region.map.summary').read_text()
        costs[side]={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',summary)[1].replace(',','')) for k,v in fields.items()}
        raw=(d/'output_files/region.map.rpt').read_text();hierarchy[side]={}
        for line in raw.splitlines():
            if not line.startswith(';'):continue
            cols=[x.strip() for x in line.split(';')[1:-1]]
            if cols and re.fullmatch(r'\|(nes_source589|nes_native_export203|nes_packet589|nes_native_spi\d+|nes_native_mailbox165):[^|]+\|',cols[0]):
                hierarchy[side][cols[0]]=dict(comb_inclusive=int(cols[1].split()[0]),FF_inclusive=int(cols[2].split()[0]),RAM_bits=int(cols[3]))
        machines[side]=sorted(set(re.findall(r'^; State Machine - (.+?)\s*;',raw,re.M)))
        log=(d/'map.log').read_text();assert not re.search(r'Warning \((10034|10240)\)',log)
        warnings[side]=sorted(set(re.findall(r'Warning \((\d+)\)',log)))
        pins[side]={n:sha(d/n) for n in ('map.log','output_files/region.map.rpt','output_files/region.map.summary')}
    assert 'M9K  ; Single Port' in (a.map/'candidate/output_files/region.map.rpt').read_text()
    delta={k:costs['candidate'][k]-costs['reference'][k] for k in fields}
    assert delta['LE']>148 and delta['RAM_bits']==24576
    assert not any('|state' in x and 'nes_source589' in x for x in machines['candidate'])
    stats=[]
    for l in (a.test/'stats.txt').read_text().splitlines():
        stats.append(dict(zip(('generation','source_ticks','queries','query_wait_ticks','RAM_writes','canonical_crc_bytes','mailbox_blocked_ticks'),map(int,l.split()))))
    groups={}
    for label,rows in [('cold',stats[:1]),('warm',stats[2:]),('dense',[r for r in stats if 951<=r['generation']<=955])]:
        groups[label]={k:dict(mean=statistics.mean(r[k] for r in rows),minimum=min(r[k] for r in rows),maximum=max(r[k] for r in rows)) for k in stats[0] if k!='generation'}
    toolpins={n:sha(ROOT/n) for n in ('rtl/nes_source589.sv','tools/check_nes_source589.py','tools/analyze_nes_source589.py')}
    assert toolpins['rtl/nes_source589.sv']==result['source_pins']['nes_source589.sv']
    assert maps['results']['candidate']['inputs']['nes_source589.sv']==toolpins['rtl/nes_source589.sv']
    report=dict(stage=589,functional_passed=True,frames=53,packets=result['packets'],guards=8,
        input_scope='Pinned captured query values, latency3..5 source edges, real paired-clock source/mailbox/host SPI pins. Not actual collector/ROM/ARM/65816.',
        test_clock=dict(source_period_ns=45.454,host_period_ns=11.904,host_phase_ns=3.5,SPI_bit_period_ns=380.952380952),
        costs=costs,delta=delta,hierarchy=hierarchy,extracted_state_machines=machines,warnings=warnings,
        RAM='Source3072x8 single-port M9K +host256x8 simple-dual M9K inferred; physical block packing/FIT not measured',
        stats=stats,groups=groups,selection='REJECT current generic source controller on area; stop ARM expansion as planned',
        comparison_boundary='Both local MAP wrappers include unchanged17bit PREPARE mailbox; differs from wholeFIT1433LE ledger. Never subtract local MAP from wholeFIT.',
        key_limit='LocalMAP delta is not a placed whole-board deficit. It gives no credible route within148LE whole margin.',
        state_machine_limit='Source uses state<=ret/query_ret/byte_ret; not extracted as FSM. Return dispatch/variable address/width selection remains. No isolated FSM/seed/opcode iteration approved.',
        new_ARM=False,new_whole_FIT=False,new_STA=False,new_physical_FPS=False,new_package=False,
        evidence=pins,tool_pins=toolpins,inputs=result['source_pins'],
        next_gate='R2 role/protocol re-selection: compare fixed-row summary/request with ARM-owned reuse decision against baseline577; account all request/CDC/CRC/cold-fallback/Flash/output residual costs before another implementation. Do not grow589 or tune FSM attributes.')
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'result.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    # Preserve this turn's raw evidence locally, excluding Quartus databases and
    # all floating-license server files. No archive is added to Git.
    with zipfile.ZipFile(a.out/'evidence.private.zip','w',zipfile.ZIP_DEFLATED) as z:
        for prefix,root in (('test',a.test),('map',a.map)):
            for p in root.rglob('*'):
                rel=p.relative_to(root)
                if not p.is_file() or any(x in ('db','incremental_db','work') for x in rel.parts):continue
                if p.suffix.lower() in ('.sv','.json','.log','.txt','.values','.counts','.rpt','.summary','.qsf','.qpf'):
                    z.write(p,prefix+'/'+rel.as_posix())
    (a.out/'archive.json').write_bytes((json.dumps(dict(sha256=sha(a.out/'evidence.private.zip'),bytes=(a.out/'evidence.private.zip').stat().st_size),indent=2)+'\n').encode('utf8'))
    print(json.dumps(dict(functional_passed=True,frames=53,packets=report['packets'],guards=8,costs=costs,delta=delta,selected=False),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('test','map','out'):p.add_argument('--'+n,type=Path,required=True)
    analyze(p.parse_args())
