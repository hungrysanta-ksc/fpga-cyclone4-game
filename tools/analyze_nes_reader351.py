# SPDX-License-Identifier: MIT
"""Whole-cost/port/timing comparison of reader351 against selected338/336."""
import argparse,csv,json,re
from collections import Counter,defaultdict
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_receipt335 import load_image
from probe_nes_decode280 import records,golden

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=BASE/'probes/nes-reader351');ap.add_argument('--partial',action='store_true');a=ap.parse_args()
    pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    old=js(ROOT/'analysis/port350-verification.json')
    for n,h in old['pins'].items():assert sha(Path(n))==h,n;pins[n]=h
    base=js(ROOT/'analysis/ingress338-verification.json');runs={}
    for tag,ref in [('window01','window03'),('fixed01','fixed01'),('normal01','normal01')]:
        d=a.root/tag;b=BASE/'probes/nes-ingress338'/ref
        if not (d/'result.json').exists():assert a.partial,tag;continue
        r=js(d/'result.json');br=js(b/'result.json');assert r['passed']
        changed={n for n,h in r['rtl_hashes'].items() if h!=br['rtl_hashes'][n]}
        assert changed=={'nes_mux260.sv','nes_queue260.sv'},changed
        for n,h in r['rtl_hashes'].items():assert sha(d/n)==h;read(d/n)
        assert r['ARM']==br['ARM'],(tag,'ARM cost/state changed')
        for n in ('nes_delta231.c','nes_planner211.c','nes_decode280.c','nes_refill267.c'):
            assert sha(d/n)==sha(b/n),(tag,n,'unchanged ARM source');read(d/n)
        assert load_image(d/'output.elf')==load_image(b/'output.elf');pins[str(d/'output.elf')]=sha(d/'output.elf')
        for n in ('cycles.csv','blocks.txt','joint-events.csv','CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc'):
            pins[str(d/n)]=sha(d/n);assert sha(d/n)==sha(b/n),(tag,n)
        assert 'PASS REFILL267 frames=3' in read(d/'vsim.log')
        assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log')
        assert sha(d/'joint266_tb.sv')==r['tb_sha256'];read(d/'joint266_tb.sv')
        def ports(p):return list(csv.DictReader(read(p).splitlines()))
        pp=ports(d/'ports350.csv');bp=ports(BASE/f'probes/nes-port350/{tag}/ports350.csv')
        profile=js(d/'metadata317.json');rows=[]
        for fi,f in enumerate((905,906,907)):
            assert js(d/f'arm{f}.json')==js(b/f'arm{f}.json')
            rr=[x for x in pp if x['frame']==str(f)];prior=[x for x in bp if x['frame']==str(f)]
            # Header captures are reordered; compare completed field/address maps
            # per immutable queue head. All nonheader captures retain byte order/time.
            def header(xs):
                out=defaultdict(dict)
                for x in xs:
                    if x['state']=='55' and x['capture']=='1':
                        key=int(x['retired']);addr=int(x['previous_addr']);assert addr not in out[key]
                        out[key][addr]=int(x['read_data'])
                return dict(out)
            assert header(rr)==header(prior),(tag,f,'header fields')
            def capture(xs):return [(x['time'],x['previous_addr'],x['read_data']) for x in xs if x['capture']=='1' and x['state']!='55']
            assert capture(rr)==capture(prior),(tag,f,'common response order/time')
            def expected(xs):return [(x['time'],x['read_addr'],x['write_data']) for x in xs if x['expected_write']=='1']
            assert expected(rr)==expected(prior),(tag,f,'expected write')
            def final(xs):return [(x['time'],x['previous_addr'],x['read_data']) for x in xs if x['op']=='3' and x['validator_state']=='32']
            assert final(rr)==final(prior) and len(final(rr))==446
            assert sum(x['state']=='55' for x in rr)==sum(x['state']=='55' for x in prior)
            for x in rr:
                assert ((int(x['accepted'])-int(x['retired']))&65535)<=2
                assert x['reset']=='0' and x['fault']=='0'
            prep={}
            for name in ('nes_dirty231_begin','nes_dirty231_material','start286','geometry286','expand286','h2early286','begin285'):
                matches=[x for x in profile if x['name']==name]
                assert len(matches)==3,(tag,name,len(matches))
                x=matches[fi];n=x['end']['instruction']-x['start']['instruction']
                prep[name]=dict(instructions=n,CPI1_ms=n/84000)
            assert prep['nes_dirty231_material']['instructions']+prep['nes_dirty231_begin']['instructions']<=prep['start286']['instructions']
            rows.append(dict(frame=f,timing=next(x for x in base['runs'][ref]['rows'] if x['frame']==f),
                header_packets=len(header(rr)),header_captures=sum(len(v) for v in header(rr).values()),
                nonheader_captures=len(capture(rr)),expected_writes=len(expected(rr)),independent_captures=len(final(rr)),
                first_BG_prepare=prep,unchanged_time=True,header_pipeline_clocks_unchanged=True))
        runs[tag]=dict(rows=rows,only_two_RTL_modules_changed=True,ARM_image_and_execution_unchanged=True,
                       all_original_events_exact=True,header_field_maps_exact=True,common_returns_and_expected_exact=True)
    board=None;d=a.root/'map01'
    if (d/'result.json').exists():
        r=js(d/'result.json');assert r['passed']
        for n,h in r['actual_inputs'].items():assert sha(d/n)==h;pins[str(d/n)]=h
        log=read(d/'map.log');assert 'Warning (10034)' not in log
        assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
        if runs:
            for n in ('nes_queue260.sv','nes_core257.sv','nes_validator278.sv','nes_spi270.sv','nes_plan_spi200.sv'):
                assert sha(d/n)==sha(a.root/'window01'/n),(n,'MAP/schedule binding')
            # Inherited MAP wrapper retains one extra blank line at module end.
            assert read(d/'nes_transport257.sv').replace('\n\nendmodule','\nendmodule')==read(a.root/'window01/nes_transport257.sv')
            host=read(d/'nes_mux260.sv').replace(' output wire tile_closed267,\n','').replace('reg tiles_closed;assign tile_closed267=tiles_closed;','reg tiles_closed;')
            assert host==read(a.root/'window01/nes_mux260.sv')
        report=read(d/'output_files/board.map.rpt');nodes={}
        for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
            c=[x.strip() for x in line.split(';')]
            if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
        whole={k:int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',','')) for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
        assert sum(nodes.values())==whole['comb']
        assert 'State Machine - |fxpak_nes_screen137_top|nes_live_joint:core|nes_joint267_board:native_joint267|nes_output260:flow|state' in report
        board=dict(whole=whole,delta={k:whole[k]-base['whole'][k] for k in whole},comb_deficit=whole['comb']-15408,
                   entity_own_comb=nodes,entity_delta={k:v-base['own_entity_comb'][k] for k,v in nodes.items()},host_FSM_extracted=True)
    else:assert a.partial,'MAP'
    guards=None;d=a.root/'guards01'
    if (d/'result.json').exists():
        guards=js(d/'result.json');assert guards['passed']
        assert guards['rtl_hashes']==js(a.root/'window01/result.json')['rtl_hashes']
        read(d/'joint266_tb.sv')
        for c in guards['cases']:
            t=d/f"case{c['case']}";log=read(t/'vsim.log');assert sha(t/'vsim.log')==c['log_sha256'];read(t/'ports350.csv')
            assert 'INJECT350' in log and f"PASS OWNER319 GUARD={c['case']}" in log
        for name in ('aperture','final-raw0'):
            g=js(d/name/'result.json');assert g['passed'];guards[name]=g
            for p in (d/name).iterdir():
                if p.is_file() and p.suffix in ('.sv','.log'):read(p)
    else:assert a.partial,'guards'
    raw_review=[]
    if runs:
        def material(raw):
            out=bytearray(2048)
            for group in range(32):
                for plane in range(4):
                    at=group*64+plane*16
                    for slot in range(len(raw)//256):
                        for bit in range(8):
                            c=64+raw[slot*256+group*8+bit]
                            out[at+slot*2]|=((c>>(plane*2))&1)<<(7-bit)
                            out[at+slot*2+1]|=((c>>(plane*2+1))&1)<<(7-bit)
            return out
        previous_raw=None;previous_material=None
        for f in (905,906,907):
            path=a.root/f'window01/frame{f}.records';read(path);rr=records(path)
            for n in ('records','expected'):read(BASE/f'probes/nes-joint278/test07/frame{f}.{n}')
            _,expected_raw=golden(f);current=bytearray(previous_raw or bytes(512));phase=False;changed=[]
            for r in rr:
                if r[:4]==bytes([255,255,0,3]):phase=True
                elif r[:4]==bytes([255,255,0,4]):phase=False
                elif phase:
                    at=9
                    for i in range(64):
                        if r[1+i//8]&(1<<(i%8)):
                            pos=(r[0]-68)*64+i;current[pos]=r[at];at+=1;changed.append(pos)
                    assert at==len(r)
            assert current==expected_raw
            groups=sorted({(i%256)//8 for i in changed});dense=material(current)
            if previous_raw is None:assert groups==list(range(32))
            else:
                candidate=bytearray(previous_material)
                for g in groups:candidate[g*64:g*64+64]=dense[g*64:g*64+64]
                assert candidate==dense
            raw_review.append(dict(frame=f,changed_source_pixels=len(changed),affected_groups=groups,
                full_conversion_bytes=2048,affected_conversion_bytes=64*len(groups),
                model_scope='Python dependency/reconstruction only; its dense arrays are not proposed ARM storage. No optimized M4 execution or time saving measured. Requires input-history/display identity and STOP invalidation proof.'))
            previous_raw=current;previous_material=dense
    for n in ('nes_reader351.py','probe_nes_reader351.py','map_nes_reader351.py','guard_nes_reader351.py','analyze_nes_reader351.py'):read(ROOT/'tools'/n)
    out=dict(stage=351,passed=True,complete=not a.partial,status='candidate_rejected_area_regression' if board else 'pending',
        selected_RTL=338,selected_ARM=336,new_RTL=True,new_ARM=False,new_MAP=True,
        prior_pins_rehashed=len(old['pins']),runs=runs,board=board,guards=guards,raw_group_review=raw_review,pins=pins,
        scope='Actual common reader on338 with unchanged336 M4 instruction/IRQ model; same whole Lite MAP. No FIT/STA/fullRUN/physical60fps.')
    if not a.partial:(ROOT/'analysis/reader351-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
    print(json.dumps({k:v for k,v in out.items() if k!='pins'},indent=2))

if __name__=='__main__':main()
