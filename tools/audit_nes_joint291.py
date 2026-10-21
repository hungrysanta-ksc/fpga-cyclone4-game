# SPDX-License-Identifier: MIT
"""Read-only ownership/area audit of the retained 287 RTL and native289 traces.

No new RTL performance, gate saving, or formal verification is inferred here.
The ownership list is a reviewed contract; anchors bind it to actual source.
"""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from nes_delta231 import BASE, ROOT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    pins = {}

    def read(p):
        data = p.read_bytes()
        pins[str(p)] = hashlib.sha256(data).hexdigest()
        return data.decode('utf-8-sig')

    def js(p):
        return json.loads(read(p))

    prior = js(ROOT / 'analysis/joint287-verification.json')
    native = js(ROOT / 'analysis/joint289-verification.json')
    rejected = js(ROOT / 'analysis/joint290-verification.json')
    assert prior['passed'] and native['passed'] and rejected['passed']
    sim = BASE / 'probes/nes-joint289/test02'
    board = BASE / 'probes/nes-joint287/board01'
    own = {}
    for line in read(board / 'output_files/board.map.rpt').splitlines():
        f = [x.strip() for x in line.split(';')]
        if len(f) == 14 and re.fullmatch(r'\d+ \(\d+\)', f[2]):
            own[f[10]] = {k: int(re.search(r'\((\d+)\)', f[i]).group(1))
                          for k, i in [('comb', 2), ('FF', 3)]}
    assert sum(x['comb'] for x in own.values()) == 17671
    assert prior['area']['expanded_boundary'] == 4853
    assert prior['area']['expanded_budget'] == 2590
    # The native producer changed the ARM, not the retained RTL.
    result = js(sim / 'result.json')
    for name, expected in result['rtl_hashes'].items():
        text = read(sim / name)
        assert pins[str(sim / name)] == expected
        assert (sim / name).read_bytes() == (BASE / 'probes/nes-joint287/test06' / name).read_bytes(), name

    def region(suffix, subtree=False):
        return sum(v['comb'] for k, v in own.items()
                   if (suffix in k if subtree else k.endswith(suffix)))

    regions = dict(host=region('nes_output260:flow'),
                   validator=region('nes_validator278:validator'),
                   queue=region('nes_queue260:queue', True),
                   plan=region('nes_plan_batch206:transport', True) + region('nes_plan_spi200:endpoint', True),
                   SPI=region('nes_spi270:spi_front270', True),
                   glue=region('nes_joint267_board:native_joint267') + region('nes_joint257:core'))
    assert sum(regions.values()) == 4853
    assert regions == dict(host=2361, validator=1090, queue=129, plan=568, SPI=658, glue=47)
    # These are feasibility arithmetic, NOT predicted synthesis outcomes.
    budgets = []
    for name, selected in [('host_only', ['host']), ('validator_only', ['validator']),
                           ('queue_plan_SPI_only', ['queue', 'plan', 'SPI']),
                           ('host_validator', ['host', 'validator']),
                           ('whole_fixed_boundary', list(regions))]:
        old = sum(regions[k] for k in selected)
        retained = 4853 - old
        budget = 2590 - retained
        budgets.append(dict(candidate=name,old_comb=old,retained_comb=retained,
                            replacement_budget=budget,reserve128_budget=budget-128,
                            required_reduction=2263,required_percent=100*2263/old,
                            measured_replacement_comb=None))

    # Exact source anchors + reviewed ownership; no claim of exhaustive liveness.
    rows = []
    def owner(name, file, anchor, live, decision, retained, proposal):
        lines = read(sim / file).splitlines()
        hits = [i+1 for i,x in enumerate(lines) if anchor in x]
        assert len(hits) == 1, (name, hits)
        rows.append(dict(resource=name,file=file,line=hits[0],anchor=anchor,
                         lifetime=live,decision=decision,retain=retained,replace=proposal,
                         measured_comb_saving=None))

    owner('queue credit/head','nes_queue260.sv','reg [15:0] accepted,retired;',
          'E1 accepted through parser_retire; next SPI write overlaps SNES/head read',
          'retain','4 immutable packets; accepted/retired wrap; length and CRC admission',
          'Only one combined completion event may drive parser_retire')
    owner('packet reader','nes_mux260.sv','wire [7:0] qaddr=',
          'header/internal read OR NORMAL SNES read; queue write remains concurrent',
          'replace_control','registered read latency, qtag, exact sequential SNES read proof',
          'One queue read sequencer for H2/header/map/manifest; no extra byte buffer')
    owner('ACK progress','nes_mux260.sv','wire ack_publish=',
          'ordinary reads and 12 ACK writes precede OSETUP; final ACK later',
          'retain','at already reused for header/ACK/display; ordinary_reads differs from ACK index',
          'Fold ACKWAIT dispatch into combined completion; never release on bus ACK alone')
    owner('descriptor receipt bridge','nes_mux260.sv','reg [11:0] receipt_first282,receipt_count282;',
          'descriptor held through validator walk; map/ordinary mutually exclusive',
          'replace_control','independent alignment/domain/duplicate/CRC checks and original descriptor',
          'Remove OTILE/OSELECT/SEND/WAIT_RECEIPT/ORET rendezvous in a combined host controller')
    owner('range RAM walk','nes_validator278.sv','reg [11:0] v_bit_at,v_end283,v_map_end;',
          'range endpoint live during walk; map_end persists across subsequent descriptors',
          'retain','read-before-OR duplicate detection; persistent validity after receipt; monotone map_end',
          'Single range admission and walker; map_end cannot alias per-range cursor')
    owner('manifest transport','nes_mux260.sv','reg [7:0] rle_left;reg rle_zero,tile_proven;',
          'compressed packet/RLE cursor and expanded manifest cursor both live',
          'replace_control','compressed remaining/opos and independent expanded cursor remain distinct',
          'Joint byte decode -> RAM check -> advance; remove OCHECKNEXT/ORLE ready relay, not coverage')
    owner('manifest comparison','nes_validator278.sv','V_PCHECKTEST:if(checked_byte',
          'received byte retained while receipt then persistent-valid RAM are read',
          'retain','422-byte checks including cold full map and raw0 rules',
          'Combined continuation after V_CHECKTEST/V_PCHECKTEST; keep checked_byte')
    owner('payload CRC tap','nes_mux260.sv','reg [2:0] tap_state278;',
          'NORMAL SNES read/ACK observer concurrent with H_BYTES/H_SCROLL',
          'retain_concurrent','tap position/value/pattern and CRC byte/lane progress',
          'Cannot alias with packet cursor or CRC engine simply because phases share host clock')
    owner('phase RAM ports','nes_joint257.sv','always @(posedge host_clk)begin bq',
          'port A NES source; port B host validator; source/display lease separates overlapping addresses',
          'retain','two clock domains; registered outputs and abort/fault write gates',
          'Keep validator sole port-B owner; packet RAM is a separate concurrently used memory')
    owner('plan banks','nes_plan_batch206.sv','reg pending,writer,reader,retire_pending',
          'host writes next bank while NES owns sealed bank through tile_done',
          'retain_concurrent','2 immutable bank ownership/CRC/CDC and EA retirement',
          'No phase RAM or queue bank overlay without new concurrent-capacity proof')
    owner('final display ACK','nes_mux260.sv',"if(ap==24'h006058)begin",
          'after manifest/CRC seal and all 12 exact display reads',
          'retain','owner NONE, no queue/tile request, complete token/mask, sealed, core retirement',
          'Unified final transition may drive existing mailbox; keep final ACK distinct from packet receipt')

    traces = []
    for mode, folder in [('normal','test02'), ('restricted','window01')]:
        run = BASE / 'probes/nes-joint289' / folder
        events = list(csv.reader(read(run / 'joint-events.csv').splitlines()))
        source = {int(x['frame']): x for x in csv.DictReader(read(run / 'cycles.csv').splitlines())}
        for name in ('joint-events.csv', 'cycles.csv'):
            recorded = [h for p,h in native['input_hashes'].items()
                        if p.replace('\\', '/').endswith('/'+folder+'/'+name)]
            assert recorded == [pins[str(run/name)]], (folder, name)
        tb = read(run / 'joint266_tb.sv')
        assert '$time-parser_start264' in tb and '$time-receipt_start' in tb
        for baseline in native['normal' if mode == 'normal' else 'restricted']:
            f = baseline['frame']; es = [e for e in events if int(e[1]) == f]
            done = [e for e in es if e[0] == 'frame_done']
            assert len(done) == 1
            total = int(source[f]['total'])*45.454/1e6 + int(done[0][3])/1e9
            assert abs(total-baseline['total_ms']) < 1e-10
            parser = sum(int(e[3]) for e in es if e[0] == 'parser') / 1e9
            receipt = sum(int(e[3]) for e in es if e[0] == 'receipt') / 1e9
            # A deliberately generous zero-cost thought experiment for these
            # recorded windows only; overlapping intervals may double count.
            # It is not a global bound under changed ROM/polling phase.
            traces.append(dict(mode=mode,frame=f,total_ms=baseline['total_ms'],
                               parser_windows_ms=parser,map_receipt_windows_ms=receipt,
                               diagnostic_sum_ms=parser+receipt,
                               frozen_schedule_zero_windows_ms=baseline['total_ms']-parser-receipt,
                               margin_ms=baseline['margin_ms'],
                               measured_new_time_ms=None))

    early = [dict(frame=x['frame'],early_DMA=x['early_packets']-1) for x in rejected['native_frames']]
    assert len(early) == 71 and [(x['frame'],x['early_DMA']) for x in early if x['early_DMA']] == [(906,5)]
    result = dict(stage=291,passed=True,kind='source_and_existing_evidence_audit',
                  functional_reference=289,performance_reference=287,regions=regions,
                  whole_comb=17671,whole_limit=15408,deficit=2263,
                  fixed_boundary=4853,outside=12818,budget=2590,reserve128_budget=2462,
                  budgets=budgets,ownership=rows,traces=traces,early_DMA=early,
                  measured_new_saving_comb=None,measured_new_time_ms=None,
                  new_RTL=False,new_MAP=False,new_simulation=False,P2_selected=False,
                  decision='No evidence-backed area-fit candidate yet; joint controller specification only.',
                  input_hashes=pins,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    for name, data in [('ownership', rows),('budgets',budgets),('timing',traces)]:
        with (a.out / (name+'.csv')).open('w',newline='',encoding='utf-8') as fp:
            w=csv.DictWriter(fp,fieldnames=list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
    (a.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,budgets=budgets,traces=traces),ensure_ascii=False))


if __name__ == '__main__':
    main()
