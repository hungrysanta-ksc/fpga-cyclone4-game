# SPDX-License-Identifier: MIT
"""Same-boundary timing and whole Lite ledger for the common executor."""
import argparse,csv,json,re,collections
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--restricted',required=True)
    ap.add_argument('--normal',required=True);ap.add_argument('--board',required=True)
    ap.add_argument('--guards',required=True);ap.add_argument('--early',required=True);a=ap.parse_args()
    d=BASE/'probes/nes-executor313';pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    base=js(ROOT/'analysis/ingress307-verification.json')
    old=js(ROOT/'analysis/slots312-verification.json');runs={}
    for mode,tag in [('restricted',a.restricted),('normal',a.normal)]:
        q=d/tag;r=js(q/'result.json');assert r['passed']
        for n,h in r['rtl_hashes'].items():assert sha(pin(q/n))==h
        assert sha(pin(q/'output.elf'))==r['ELF_sha256']
        assert sha(pin(q/'joint266_tb.sv'))==r['tb_sha256']
        assert all(x['pending']<2 for x in js(q/'issue307.json'))
        events=list(csv.reader(pin(q/'joint-events.csv').open()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(pin(q/'cycles.csv').open())}
        rows=[]
        for f in (905,906,907):
            ev=[x for x in events if len(x)>1 and x[1]==str(f)]
            end=next(x for x in ev if x[0]=='frame_done')
            total=source[f]+int(end[3])/1e9;finish=int(end[2])/1e9;start=finish-total
            ref=next(x for x in base[mode] if x['frame']==f)
            prior=next(x for x in old['runs'][mode]['rows'] if x['frame']==f)
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            tx=[x for x in ev if x[0]=='arm267'];assert sum(int(x[3]) for x in tx)==arm['SPI_bytes']
            first=next(x for x in ev if x[0]=='romtile305' and x[2]=='0');bg=int(first[-1])/1e9
            credit=max(int(x[2]) for x in ev if x[0]=='credits');assert credit<=2
            rows.append(dict(frame=f,total_ms=total,delta307_ms=total-ref['total_ms'],delta312_ms=total-prior['total_ms'],
                gap_ms=total-1000/60,start_ms=start,finish_ms=finish,first_BG_ms=bg,before_BG_ms=bg-start,after_BG_ms=finish-bg,
                start_delta307_ms=start-ref['frame_start_ms'],finish_delta307_ms=finish-ref['absolute_finish_ms'],
                first_BG_delta307_ms=bg-ref['first_BG_ms'],tail_delta307_ms=finish-bg-ref['tail_after_first_BG_ms'],
                ARM_instructions=arm['instructions'],SPI_bytes=arm['SPI_bytes'],max_credit=credit,
                responses={hex(cmd):dict(count=sum(int(x[2])==cmd for x in tx),wire_bytes=sum(int(x[3]) for x in tx if int(x[2])==cmd)) for cmd in (224,226,225,233)}))
        runs[mode]=dict(rows=rows,sequence_delta307_ms=sum(x['delta307_ms'] for x in rows),stack=r['ARM']['stack_observed'],ELF_sha256=r['ELF_sha256'])
    board=js(d/a.board/'result.json');assert board['passed']
    for n,h in board['actual_inputs'].items():assert sha(pin(d/a.board/n))==h
    def metric(label):return int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',board['summary'])[1].replace(',',''))
    whole={k:metric(v) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    def normalize(s):return s.replace(' output wire tile_closed267,\n','').replace('reg tiles_closed;assign tile_closed267=tiles_closed;','reg tiles_closed;')
    for n in ('nes_mux260.sv','nes_queue260.sv','nes_validator278.sv','nes_spi270.sv'):
        ref=pin(d/a.restricted/n).read_text()
        assert normalize(pin(d/a.board/n).read_text())==ref,('board',n)
        assert pin(d/a.normal/n).read_text()==ref,('normal',n)
        assert pin(d/a.guards/n).read_text()==ref,('guards',n)
    checks=js(d/a.guards/'result.json');assert checks['passed'] and checks['positive_control313']
    early=js(d/a.early/'result.json');assert early['passed'] and early['manifest_new_index']==2
    for name,h in early['actual_inputs'].items():assert sha(pin(d/a.early/name))==h
    for name in ('nes_mux260.sv','nes_queue260.sv','nes_validator278.sv','nes_spi270.sv'):
        assert sha(d/a.early/name)==sha(d/a.restricted/name),('early source',name)
    cpu=js(d/'cpu03/result.json');assert cpu['passed'] and cpu['CPU']['commands']==544
    for n in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
        assert sha(pin(d/'cpu03'/n))==sha(pin(d/a.restricted/('CPU-'+n)))
    loads=[]
    for q in (BASE/'probes/nes-slots312/window06',d/a.restricted,d/a.normal):
        with pin(q/'output.elf').open('rb') as f:
            loads.append([(x['p_vaddr'],x['p_memsz'],x.data()) for x in ELFFile(f).iter_segments() if x['p_type']=='PT_LOAD'])
    assert loads[0]==loads[1]==loads[2], 'ARM executable/data segments changed'
    cpu_cost={}
    for tag,q in [('279',BASE/'probes/nes-joint279/cpu01'),('313',d/'cpu03')]:
        timing=list(csv.DictReader(pin(q/'timing.csv').open()));serials={int(x['case']):int(x['serial']) for x in timing}
        bus=list(csv.DictReader(pin(q/'bus.csv').open()));by_case=collections.defaultdict(list)
        for x in bus:by_case[int(x['case'])].append(int(x['clock']))
        cpu_cost[tag]=dict(bus_events=len(bus),bus_span_clocks={str(f):sum(max(v)-min(v) for k,v in by_case.items() if serials[k]==f-904) for f in (905,906,907)},
            CSV_partial_clocks={str(f):sum(int(x['total_clocks']) for x in timing if int(x['serial'])==f-904) for f in (905,906,907)})
    own={};fsm={}
    for tag,q in [('307',BASE/'probes/nes-ingress307/board03'),('313',d/a.board)]:
        own[tag]={}
        report=pin(q/'output_files/board.map.rpt').read_text()
        fsm[tag]={name:('State Machine - |' in report and bool(re.search(r'State Machine - .*\|'+re.escape(path)+r'\|state\s',report)))
                  for name,path in [('host','nes_output260:flow'),('validator','nes_validator278:validator')]}
        for line in report.splitlines():
            c=[x.strip() for x in line.split(';')]
            if len(c)>4 and c[1] in ('|nes_output260:flow|','|nes_queue260:queue|','|nes_validator278:validator|','|nes_spi270:spi_front270|'):
                own[tag][c[1]]=dict(comb=int(re.search(r'\((\d+)\)',c[2])[1]),FF=int(re.search(r'\((\d+)\)',c[3])[1]))
        assert len(own[tag])==4
    tracked_delta=sum(own['313'][k]['comb']-own['307'][k]['comb'] for k in own['307'])
    other_delta=whole['comb']-base['whole_MAP']['comb']-tracked_delta
    host=(d/a.restricted/'nes_mux260.sv').read_text();v=(d/a.restricted/'nes_validator278.sv').read_text()
    queue=(d/a.restricted/'nes_queue260.sv').read_text()
    for x in ('ACKWAIT:','OSETUP:','OTILE,OSELECT:','ack_expected','ack_publish'):assert x not in host,x
    for x in ('packet_at298','executing298','E_READ298','E_ZERO298','complete_execution298'):assert x not in v,x
    assert 'virtual312' not in queue
    result=dict(stage=313,passed=True,selected=False,runs=runs,whole_MAP=whole,
      delta307={k:whole[k]-base['whole_MAP'][k] for k in whole},delta312={k:whole[k]-old['whole_MAP'][k] for k in whole},
      comb_deficit=whole['comb']-15408,checks=checks,early_manifest_stress=early,CPU=cpu,CPU_cost=cpu_cost,own_resources=own,FSM_extraction=fsm,
      tracked_own_comb_delta=tracked_delta,other_whole_comb_delta=other_delta,
      unchanged_ARM_PT_LOAD=True,reused_ARM_guards='NES312 counter/CRC/credit20 and supply20, not new test runs',
      limits=['Actual M4 instructions at modeled CPI1/84MHz; IRQ body, fixed ROM competition and two-slot responses included.',
       'New actual 65816 ordinary kernel measured separately and its bus trace replayed against RTL. Tile/map and VBlank/final display retain modeled service; no full-system live 65816 proof.',
       'Only 905..907 retimed; no whole71/full ARM RUN/FIT/STA/physical 60fps.',
       'SPI/plan FSMs retained; 32B RAM directory reservation unused; reception cursors are registers.'],input_hashes=pins)
    for n in ('nes_executor313.py','nes_manifest313.py','nes_consumer313.py','nes_admission313.py','probe_nes_consumer313.py','probe_nes_live313.py','map_nes_executor313.py','guard_nes_executor313.py','probe_nes_early313.py','analyze_nes_executor313.py'):pin(ROOT/'tools'/n)
    (ROOT/'analysis/executor313-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({k:result[k] for k in ('runs','whole_MAP','delta307','delta312','comb_deficit')},indent=2))


if __name__=='__main__':main()
