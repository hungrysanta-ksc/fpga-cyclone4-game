# SPDX-License-Identifier: MIT
"""Bind aligned queue and immutable D4 to unchanged schedules and whole Lite."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_receipt335 import load_image


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');args=ap.parse_args()
    root=BASE/'probes/nes-ingress338';pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    prior=js(ROOT/'analysis/read336-verification.json');schedule=js(ROOT/'analysis/ingress337-verification.json')
    runs={};rtl=None
    for tag,ref in [('window03','window01'),('fixed01','fixed01'),('normal01','normal01')]:
        d=root/tag;old=BASE/'probes/nes-ingress337'/ref
        r=js(d/'result.json');pr=js(old/'result.json');assert r['passed'] and r['ARM']==pr['ARM']
        assert {n for n,h in r['rtl_hashes'].items() if h!=pr['rtl_hashes'][n]}=={'nes_queue260.sv','nes_transport257.sv'}
        if rtl is None:rtl=r['rtl_hashes']
        else:assert rtl==r['rtl_hashes']
        for n,h in rtl.items():assert sha(d/n)==h;read(d/n)
        assert sha(d/'joint266_tb.sv')==r['tb_sha256'];read(d/'joint266_tb.sv')
        assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log')
        assert load_image(d/'output.elf')==load_image(old/'output.elf');pins[str(d/'output.elf')]=sha(d/'output.elf')
        for n in ('CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc','cycles.csv','source-ARM-blocks.csv','source-ARM-decoder.elf'):
            pins[str(d/n)]=sha(d/n);assert sha(d/n)==sha(old/n),(tag,n)
        for p in d.iterdir():
            if p.is_file() and p.suffix in ('.hex','.expected','.palette','.lens','.desc'):
                pins[str(p)]=sha(p);assert (old/p.name).exists() and sha(p)==sha(old/p.name),(tag,p.name,'fixture changed')
        ev=list(csv.reader(read(d/'joint-events.csv').splitlines()))
        assert ev==list(csv.reader(read(old/'joint-events.csv').splitlines())),(tag,'timeline changed')
        assert js(d/'calls337.json')==js(old/'calls337.json')
        block_text=read(d/'blocks.txt');assert block_text==read(old/'blocks.txt')
        blocks=[line.split() for line in block_text.splitlines() if line.split()[0]=='907']
        payload=[bytes.fromhex(x[3]) for x in blocks]
        assert list(map(len,payload))==[237,246,28]
        assert payload[-1][:4]==bytes.fromhex('ffff0003') and payload[-1][-6:-2]==bytes.fromhex('ffff0004')
        geometry=dict(block_lengths=[237,246,28],geometry_record_bytes=10,bytes_before_geometry=483,tail_after_geometry_bytes=18,
            forced_geometry_flush_extra_blocks=1,extra_wire_bytes=15,extra_gap_us=8,
            extra_SPI_occupancy_us=15*8/2625000*1e6+8,
            scope='Packet split model only; excludes new ARM prefix/CRC, polling, source publish and shared SPI contention. Not measured frame gain.')
        rows=[]
        for oldrow in prior['runs'][ref]['rows']:
            f=oldrow['frame'];a=js(d/f'arm{f}.json');b=js(old/f'arm{f}.json');assert a==b
            rows.append(dict(oldrow,delta_ms=0.0,instruction_delta=0,SPI_delta=0,request_delta_ms=0.0,accept_delta_ms=0.0,post_ROM_delta_ms=0.0,start_delta_ms=0.0,finish_delta_ms=0.0))
        runs[tag]=dict(rows=rows,unchanged_full_event_timeline=True,source_BG_schedule=schedule['runs'][ref],geometry_boundary=geometry,ARM_summary={k:r['ARM'][k] for k in ('stack_observed','hardware_cycles','full_RUN','IRQ_entry_exit_cycles','IRQ_body_service_boundary','IRQ_preemption_modeled')})
    br=js(root/'board01/result.json');oldbr=js(BASE/'probes/nes-read336/board01/result.json');assert br['passed']
    assert {n for n,h in br['actual_inputs'].items() if h!=oldbr['actual_inputs'].get(n)}=={'nes_queue260.sv','nes_transport257.sv'}
    for n,h in br['actual_inputs'].items():read(root/'board01'/n);assert sha(root/'board01'/n)==h
    assert sha(root/'board01/nes_queue260.sv')==rtl['nes_queue260.sv']
    # Existing board export has exactly one additional blank before endmodule.
    # Prove the same pre-existing difference on336, then normalize only it.
    for stage,case in [('nes-read336','window01'),('nes-ingress338','window03')]:
        board=read(BASE/'probes'/stage/'board01/nes_transport257.sv')
        assert board.count(' assign status270=0;\n\n\nendmodule')==1
        assert board.replace(' assign status270=0;\n\n\nendmodule',' assign status270=0;\n\nendmodule')==read(BASE/'probes'/stage/case/'nes_transport257.sv')
    report=read(root/'board01/output_files/board.map.rpt');log=read(root/'board01/map.log')
    assert 'Warning (10034)' not in log
    assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
    whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',br['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    nodes={}
    for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
        c=[x.strip() for x in line.split(';')]
        if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
    assert sum(nodes.values())==whole['comb']
    def own(suffix):
        v=[v for k,v in nodes.items() if k.endswith(suffix)];assert len(v)==1;return v[0]
    def tree(suffix):
        p=[k for k in nodes if k.endswith(suffix)];assert len(p)==1
        return sum(v for k,v in nodes.items() if k==p[0] or k.startswith(p[0]+'|'))
    groups=dict(host_validator_aperture=own('nes_output260:flow')+own('nes_validator278:validator')+own('nes_bulk_aperture188:shared_ram.aperture'),queue_SPI=own('nes_queue260:queue')+own('nes_spi270:spi_front270'),source=own('nes_core257:encoder')+tree('nes_transport257:transport'),plan=own('nes_plan_path267:retained_plan267')+tree('nes_plan_batch206:transport')+own('nes_plan_spi200:endpoint'))
    if args.partial:
        print(json.dumps(dict(schedule_and_area_passed=True,whole=whole,groups=groups,outside_comb=whole['comb']-sum(groups.values()),warm={k:v['rows'][-1]['total_ms'] for k,v in runs.items()}),indent=2));return
    unit=js(root/'unit01/result.json');assert unit['passed']
    for p,h in unit['actual_inputs'].items():assert sha(Path(p))==h
    for name,module in [('nes_queue260.sv','nes_queue_old'),('nes_transport257.sv','nes_transport_old')]:
        assert read(root/'unit01'/(module+'.sv'))==read(BASE/'probes/nes-read336/window01'/name).replace('module '+name[:-3]+'(','module '+module+'(')
        read(root/'unit01'/name);assert sha(root/'unit01'/name)==rtl[name]
    name='nes_native_mailbox206.sv';read(root/'unit01'/name);assert sha(root/'unit01'/name)==rtl[name]
    from check_nes_ingress338 import TB
    assert read(root/'unit01/ingress338_tb.sv')==TB
    raw=read(root/'unit01/vsim.log');assert 'PASS338 queue=1428' in raw and raw==unit['log']
    assert all('[TFMPC]' in w for w in re.findall(r'\*\* Warning:[^\r\n]+',raw))
    guards=js(root/'guards01/result.json');assert guards['passed'] and guards['rtl_hashes']==rtl
    assert guards['ELF_sha256']==sha(root/'window03/output.elf')
    assert sorted(x['case'] for x in guards['cases'])==[3,5,6,7,9,10,17,18,19,20,21,22,23]
    assert sha(root/'guards01/joint266_tb.sv')==guards['tb_sha256'];read(root/'guards01/joint266_tb.sv')
    for row in guards['cases']:p=root/f"guards01/case{row['case']}/vsim.log";read(p);assert sha(p)==row['log_sha256']
    for sub,file in [('final-raw0','nes_validator278.sv'),('aperture','nes_bulk_aperture188.sv')]:
        d=root/'guards01'/sub;r=js(d/'result.json');assert r['passed'] and r['RTL_sha256']==rtl[file]
        tb='final332_tb.sv' if sub=='final-raw0' else 'aperture325_tb.sv'
        for n,key in [(file,'RTL_sha256'),(tb,'tb_sha256'),('vsim.log','log_sha256')]:read(d/n);assert sha(d/n)==r[key]
    for n in ('nes_ingress338.py','probe_nes_ingress338.py','map_nes_ingress338.py','check_nes_ingress338.py','guard_nes_ingress338.py','analyze_nes_ingress338.py'):read(ROOT/'tools'/n)
    delta={k:whole[k]-prior['whole'][k] for k in whole}
    out=dict(stage=338,passed=True,selected_RTL=338,selected_ARM=336,runs=runs,whole=whole,whole_delta=delta,comb_deficit=whole['comb']-15408,groups=groups,outside_comb=whole['comb']-sum(groups.values()),own_entity_comb=nodes,own_entity_delta={k:v-prior['own_entity_comb'].get(k,0) for k,v in nodes.items() if v!=prior['own_entity_comb'].get(k,0)},new_measured_gain_ms=0,guards=guards,unit=unit,scope='Actual shared-SPI/ARM instruction/IRQ model, exact schedule comparison; whole Lite MAP, not FIT/STA or physical60fps.',pins=pins)
    (ROOT/'analysis/ingress338-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,whole=whole,delta=delta,comb_deficit=out['comb_deficit'],entity_delta=out['own_entity_delta'],pins=len(pins)),indent=2))


if __name__=='__main__':main()
