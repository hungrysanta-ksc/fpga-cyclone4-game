# SPDX-License-Identifier: MIT
"""Actual340 source banks, live M4 checkpoints, independent reads, whole MAP."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_decode280 import records,chunks
from analyze_nes_receipt335 import completed_unit,load_image
from probe_nes_arm264 import ELFFile
from analyze_nes_execute334 import wire

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');a=ap.parse_args()
    root=BASE/'probes/nes-hybrid340';pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    baseline=js(ROOT/'analysis/ingress338-verification.json');runs={};rtl=None
    ref_rtl=js(BASE/'probes/nes-ingress338/window03/result.json')['rtl_hashes']
    for tag,ref in [('live02','window03'),('fixed01','fixed01'),('normal01','normal01')]:
        d=root/tag
        if not (d/'result.json').exists():
            assert a.partial,tag
            continue
        r=js(d/'result.json');assert r['passed'];old=baseline['runs'][ref]
        assert {n for n,h in r['rtl_hashes'].items() if h!=ref_rtl[n]}=={'nes_core257.sv','nes_mux260.sv'}
        if rtl is None:rtl=r['rtl_hashes']
        else:assert rtl==r['rtl_hashes']
        for n,h in rtl.items():assert sha(d/n)==h;read(d/n)
        assert load_image(d/'output.elf')==load_image(root/'live02/output.elf')
        assert sha(d/'output.elf')==r['ELF_sha256'];pins[str(d/'output.elf')]=sha(d/'output.elf')
        assert sha(d/'joint266_tb.sv')==r['tb_sha256'];read(d/'joint266_tb.sv')
        assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log')
        assert 'PASS REFILL267 frames=3' in read(d/'vsim.log')
        for n in ('CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc'):
            assert sha(d/n)==sha(BASE/'probes/nes-ingress338'/ref/n);pins[str(d/n)]=sha(d/n)
        ev=list(csv.reader(read(d/'joint-events.csv').splitlines()))
        cycles={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(d/'cycles.csv').splitlines())}
        blocks=read(d/'blocks.txt').splitlines();rows=[]
        for prev in old['rows']:
            f=prev['frame'];events=[x for x in ev if len(x)>1 and x[1]==str(f)]
            first=lambda n:next(x for x in events if x[0]==n)
            start=first('start319');end=first('frame_done');request=next(x for x in events if x[0]=='firstreq305' and x[2]=='0');accept=next(x for x in events if x[0]=='rom_accept327' and x[2]=='0')
            total=cycles[f]+int(end[3])/1e9;startms=int(start[2])/1e9;endms=int(end[2])/1e9
            if 'fixed' in tag:assert startms==prev['start_ms'] and int(start[3])==prev['start_ROM_cycle']
            rr=records(d/f'frame{f}.records');expected=records(root/f'arm03/frame{f}.records');assert rr==expected
            actual=[bytes.fromhex(x.split()[3]) for x in blocks if x.split()[0]==str(f)];assert actual==chunks(expected)
            read(d/f'frame{f}.records');read(root/f'arm03/frame{f}.records')
            transfers=js(d/f'arm{f}.json')['transfers'];firste9=next(bytes.fromhex(x['tx']) for x in transfers if x['tx'].startswith('e9'))
            newwire=wire(transfers);oldwire=wire(js(BASE/f'probes/nes-ingress338/{ref}/arm{f}.json')['transfers'])
            newwire.pop(0xe9,None);oldwire.pop(0xe9,None);assert newwire==oldwire,(tag,f,'output packet material/order')
            # live02 originally omitted the zero-valued input exception term;
            # later jobs charge it explicitly. Prove no timing is missing.
            assert all(x.get('checkpoint287') and x['exception_cycles284']==0 for x in transfers[:len(actual)])
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            assert arm['decoder_excluded']==0
            inputs=[x for x in events if x[0]=='input_ARM340'];assert len(inputs)==len(actual)
            assert sum(int(x[3]) for x in events if x[0]=='arm267')==arm['SPI_bytes']
            # Every actual read-owned completed unit must reach an independent
            # private receipt job before the exact token publishes completion.
            expected_units=[];observed=[];offset=0;token=None;writes=[];published=0
            for x in events:
                if x[0]=='read336':
                    tok,op,section,pos,off,data,t=map(int,x[2:]);assert off==offset
                    if not offset:token=tok
                    assert token==tok;offset+=1
                    u=completed_unit(op,section,pos,2)
                    if u:expected_units.append((tok,int(u[0]),u[1]))
                elif x[0]=='unit336':observed.append(tuple(map(int,x[2:5])))
                elif x[0]=='private336':
                    tok,addr,value,t=map(int,x[2:]);assert tok==token;writes.append(t)
                elif x[0]=='publish336':
                    tok,n,t=map(int,x[2:]);assert token==tok and n==offset and n>0 and all(z<t for z in writes)
                    token=None;offset=0;writes=[];published+=1
            assert expected_units==observed and offset==0
            credit=max(int(x[2]) for x in events if x[0]=='credits');assert credit<=2
            rows.append(dict(frame=f,total_ms=total,delta_ms=total-prev['total_ms'],start_ms=startms,start_ROM_cycle=int(start[3]),start_delta_ms=startms-prev['start_ms'],source_ms=cycles[f],
                first_request_ms=int(request[-1])/1e9,first_accept_ms=int(accept[-1])/1e9,post_ROM_ms=endms-int(accept[-1])/1e9,
                gap_ms=total-1000/60,payload=sum(map(len,actual)),banks=len(actual),successful_source_wire=sum(map(len,actual))+15*len(actual)+8,
                input_ARM_instructions=sum(int(x[3]) for x in inputs),ARM_instructions=arm['instructions'],output_SPI_bytes=arm['SPI_bytes'],first_E9_wire=len(firste9),max_credit=credit,
                qualified_units=len(observed),published_chunks=published,live_input_checkpoints=len(inputs)))
        with (d/'output.elf').open('rb') as fp:
            elf=ELFFile(fp);sizes={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.data','.bss')}
        runs[tag]=dict(rows=rows,sizes=sizes,stack=r['ARM']['stack_observed'],IRQ_cases=len(r['ARM']['IRQ_cases']))
    b=root/'board01';br=js(b/'result.json');assert br['passed']
    old_board=js(BASE/'probes/nes-ingress338/board01/result.json')
    assert {n for n,h in br['actual_inputs'].items() if h!=old_board['actual_inputs'].get(n)}=={'nes_core257.sv','nes_mux260.sv'}
    for n,h in br['actual_inputs'].items():assert sha(b/n)==h;read(b/n)
    if rtl:
        assert sha(b/'nes_core257.sv')==rtl['nes_core257.sv']
        host=read(b/'nes_mux260.sv').replace(' output wire tile_closed267,\n','').replace('reg tiles_closed;assign tile_closed267=tiles_closed;','reg tiles_closed;')
        assert host==read(root/'live02/nes_mux260.sv')
    log=read(b/'map.log');assert 'Warning (10034)' not in log
    assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
    whole={k:int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',br['summary'])[1].replace(',','')) for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    report=read(b/'output_files/board.map.rpt');nodes={}
    for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
        c=[x.strip() for x in line.split(';')]
        if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
    assert sum(nodes.values())==whole['comb']
    codec=js(root/'arm03/result.json');guards=js(root/'armguard01/result.json');assert codec['passed'] and len(codec['frames'])==71 and guards['passed']
    for p,h in codec['input_hashes'].items():assert sha(Path(p))==h;read(Path(p))
    for name,key in [('decoder.elf','ELF_sha256'),('nes_decode280.c','C_sha256')]:
        assert sha(root/'arm03'/name)==codec[key];pins[str(root/'arm03'/name)]=codec[key]
    bg=js(root/'bgguard02/result.json');assert bg['passed'] and bg['ELF_sha256']==sha(root/'live02/output.elf')
    for n in ('nes_hybrid340.py','probe_nes_hybrid340.py','probe_nes_joint340.py','probe_nes_live340.py','guard_nes_hybrid340.py','guard_nes_joint340.py','check_nes_bg340.py','map_nes_hybrid340.py','analyze_nes_hybrid340.py'):read(ROOT/'tools'/n)
    out=dict(stage=340,passed=True,runs=runs,whole=whole,whole_delta={k:whole[k]-baseline['whole'][k] for k in whole},comb_deficit=whole['comb']-15408,
        selected=False,reason='Whole area regresses; retain338RTL+336ARM until separately justified candidate',codec_frames=71,codec_guards=len(guards['cases']),entity_own_comb=nodes,
        scope='D4/prefix instructions replayed; same actual M4 decoder/BG/planner instance charged per verified SPI bank. Ordinary536B65816 trace retained; map/tile C bus model. No physical WCET/fullRUN/FIT/STA.',pins=pins)
    if not a.partial:
        g=js(root/'guards01/result.json');assert g['passed'] and g['rtl_hashes']==rtl
        assert g['ELF_sha256']==sha(root/'live02/output.elf');out['RTL_guards']=[x['case'] for x in g['cases']]
        for x in g['cases']:
            p=root/f"guards01/case{x['case']}/vsim.log";assert sha(p)==x['log_sha256'];read(p)
        for sub in ('final-raw0','aperture'):assert js(root/'guards01'/sub/'result.json')['passed']
        out['pins']=pins;(ROOT/'analysis/hybrid340-verification.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='pins'},indent=2))
if __name__=='__main__':main()
