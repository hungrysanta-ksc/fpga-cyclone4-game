# SPDX-License-Identifier: MIT
"""Pin NES280 evidence and bound replacement budgets; no new RTL schedule."""
import argparse,csv,json,math,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--arm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    def cs(p):return list(csv.DictReader(pin(p).open()))
    b=BASE/'probes/nes-joint280';old=js(ROOT/'analysis/joint280-verification.json')
    arm=js(a.arm/'result.json');assert old['passed'] and arm['passed']
    assert arm['C_sha256']==sha(pin(ROOT/'tools/nes_boundary281.c'))
    assert arm['script_sha256']==sha(pin(ROOT/'tools/probe_nes_boundary281.py'))
    for p,h in arm['input_hashes'].items():assert sha(pin(Path(p)))==h
    assert arm['ELF_sha256']==sha(pin(a.arm/'probe.elf'))
    measurements={int(r['frame']):{k:int(v) for k,v in r.items()} for r in cs(a.arm/'frames.csv')}
    costs={int(r['frame']):{k:float(v) for k,v in r.items()} for r in cs(ROOT/'analysis/joint280-costs.csv')}
    assert len(costs)==len(measurements)==71
    # Own counts, not parent-inclusive counts: independently reconcile all comb.
    rpt=pin(b/'board01/output_files/board.map.rpt').read_text();own={}
    for line in rpt.splitlines():
        fields=[v.strip() for v in line.split(';')]
        if len(fields)==14 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):
            own[fields[10]]=int(re.search(r'\((\d+)\)',fields[2]).group(1))
    assert sum(own.values())==old['whole_MAP']['comb']==17815
    def region(part):return sum(v for k,v in own.items() if part in k)
    regions=dict(host=sum(v for k,v in own.items() if k.endswith('nes_output260:flow')),
        queue=region('nes_queue260:queue'),validator=region('nes_validator278:validator'),
        plan=region('nes_plan_batch206:transport')+region('nes_plan_spi200:endpoint'))
    assert regions==dict(host=2488,queue=129,validator=1056,plan=577)
    deficit=17815-15408;narrow=sum(regions.values())-regions['plan'];wide=sum(regions.values())
    budget=dict(current_whole=17815,device_comb=15408,deficit=deficit,own_regions=regions,
        narrow=narrow,narrow_budget=narrow-deficit,selected=wide,outside=17815-wide,
        selected_budget=wide-deficit,planning_reserve=128,selected_target=wide-deficit-128,
        whole_target=15408-128,measured_new_area=None,reclaimed=0)
    def metrics(folder):
        events=list(csv.reader(pin(folder/'joint-events.csv').open()));out={};previous=[0,0,0]
        for f in sorted({int(e[1]) for e in events}):
            es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267']
            parser=[e for e in es if e[0]=='parser'];rom=next(e for e in es if e[0]=='romwait267')
            cumulative=list(map(int,rom[2:5]));increments=[v-p for v,p in zip(cumulative,previous)]
            assert min(increments)>=0;previous=cumulative
            out[f]=dict(parser_ms=sum(int(e[3]) for e in parser)/1e9,
                manifest_parser_ms=sum(int(e[3]) for e in parser if int(e[2]) in (10,11,15))/1e9,
                receipt_ms=sum(int(e[3]) for e in es if e[0]=='receipt')/1e9,
                E2=sum(int(e[2])==226 for e in spi),
                output_SPI_bytes=sum(int(e[3]) for e in spi),
                ARM_IRQ_event_instructions=sum(int(e[5]) for e in spi),
                ROM_tile_wait_cycles=increments[0],ROM_slot_wait_cycles=increments[1],ROM_core_blocks=increments[2])
        return out
    normal=metrics(b/'test05');restricted=metrics(b/'window02');rows=[];limit=1000/60
    poll=9*8/2625+.008
    for f,c in costs.items():
        m=measurements[f];e=normal[f]
        for key in ('E2','output_SPI_bytes','ARM_IRQ_event_instructions'):assert e[key]==c[key]
        row=dict(frame=f,baseline_ms=c['diagnostic_serial_ms'],margin_ms=limit-c['diagnostic_serial_ms'],
            source_codec_instructions=int(c['source_decode_instructions']),**e,
            frozen_zero_parser_ms=c['diagnostic_serial_ms']-e['parser_ms'],
            frozen_source_CPI2_zero_parser_ms=c['frozen_source_decode_CPI2_ms']-e['parser_ms'])
        for v in ('dense','spans','compact'):
            wire=m[v+'_bytes_delta']*8/2625+m[v+'_packets_delta']*.008
            instruction=m[v+'_extra_instructions']/84000;delta=wire+instruction
            row.update({v+'_bytes_delta':m[v+'_bytes_delta'],v+'_packets_delta':m[v+'_packets_delta'],
                v+'_extra_instructions':m[v+'_extra_instructions'],v+'_wire_setup_delta_ms':wire,
                v+'_ARM_CPI1_delta_ms':instruction,v+'_added_CPI1_ms':delta,
                v+'_frozen_total_ms':c['diagnostic_serial_ms']+delta,
                v+'_frozen_zero_parser_ms':c['diagnostic_serial_ms']+delta-e['parser_ms'],
                v+'_frozen_source_and_extra_CPI2_ms':c['frozen_source_decode_CPI2_ms']+wire+2*instruction})
        rows.append(row)
    warm=[r for r in rows if r['frame']>=907];f954=next(r for r in rows if r['frame']==954)
    windows=[]
    for original in old['restricted_ROM']:
        f=original['frame'];m=next(r for r in rows if r['frame']==f)
        r=dict(frame=f,baseline_ms=original['diagnostic_serial_ms'],absolute_end_ms=original['absolute_end_ms'],**restricted[f])
        for v in ('dense','spans','compact'):r[v+'_frozen_total_ms']=r['baseline_ms']+m[v+'_added_CPI1_ms']
        r['frozen_zero_parser_ms']=r['baseline_ms']-r['parser_ms'];windows.append(r)
    assert max(warm,key=lambda r:r['baseline_ms'])['frame']==954
    for p in ('nes_mux260.sv','nes_validator278.sv','nes_plan_batch206.sv','nes_queue260.sv','joint266_tb.sv'):
        pin(b/'test05'/p)
    summary={}
    for v in ('dense','spans','compact'):
        field=v+'_frozen_total_ms';summary[v]=dict(warm_max=max(warm,key=lambda r:r[field])[field],
            warm_max_frame=max(warm,key=lambda r:r[field])['frame'],
            warm_over=[r['frame'] for r in warm if r[field]>limit],
            byte_delta_total=sum(m[v+'_bytes_delta'] for m in measurements.values()))
    reserve=.5
    needed=dict(planning_time_reserve_ms=reserve,
        normal_CPI1_for_reserve_ms=reserve-f954['margin_ms'],
        source_CPI2_to_limit_ms=f954['frozen_source_CPI2_zero_parser_ms']+f954['parser_ms']-limit,
        source_CPI2_after_zero_parser_to_limit_ms=f954['frozen_source_CPI2_zero_parser_ms']-limit,
        restricted907_to_limit_ms=windows[-1]['baseline_ms']-limit,
        E2_wire_setup_ms=poll,
        source_CPI2_poll_equivalent=math.ceil((costs[954]['frozen_source_decode_CPI2_ms']-limit)/poll))
    result=dict(passed=True,stage=281,scope='boundary and budgets plus actual ARM helper execution; frozen sensitivities only',
        baseline_commit='b2cb792a4de9ac63792a81435ca27afe6c9e8329',frames=71,packets=arm['packets'],
        ARM=arm,budget=budget,frame954=f954,variants=summary,restricted=windows,needed=needed,
        heavy=[r for r in rows if r['frame'] in (952,954,955,962,963,968,970)],
        restricted_end_ms=old['restricted_end_ms'],
        selected_prototype='Compact-wire joint host/queue/validator/plan lifecycle; retain independent byte/coverage checks.',
        new_RTL=False,new_MAP=False,new_schedule=False,new_CPU=False,full_path_ms=None,P2_selected=False,
        limits=['All existing polling, ROM competition and source/output ARM costs stay in baseline.',
          'CPI1/84MHz and source-only/added-helper CPI2 are sensitivities, not hardware WCET.',
          'Paired wire helper is not integrated serializer replacement; negative helper delta earns no credit.',
          'Parser zero subtracts all measured OSETUP-to-retire intervals optimistically, not causal/retimed saving.',
          'No parser/receipt/poll/ROM deductions are combined. E2 event instructions include intervening planner/refill work.',
          'Extra SPI/ARM costs may overlap and change ROM phase/poll counts: frozen totals are not predictions or bounds.',
          '128comb and 0.5ms are planning reserves, not proven placement or timing margin.',
          'Existing STOP/finalACK evidence is retained baseline, not proof of the proposed unified engine.'],
        input_hashes=pins,script_sha256=sha(Path(__file__)))
    with (d/'costs.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:result[k] for k in ('passed','budget','frame954','variants','needed','restricted')},ensure_ascii=False))


if __name__=='__main__':main()
