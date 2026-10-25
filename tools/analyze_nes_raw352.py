# SPDX-License-Identifier: MIT
"""Separate fixed-phase savings from continuous ROM phase movement."""
import argparse,csv,json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile
from analyze_nes_execute334 import wire
from analyze_nes_receipt335 import completed_unit,load_image

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=BASE/'probes/nes-raw352');ap.add_argument('--partial',action='store_true');a=ap.parse_args()
    pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    base=js(ROOT/'analysis/ingress338-verification.json');prior=js(ROOT/'analysis/reader351-verification.json')
    if not a.partial:
        for n,h in prior['pins'].items():assert sha(Path(n))==h,n;pins[n]=h
    runs={};image=None
    for tag,ref in [('window02','window03'),('fixed02','fixed01'),('normal02','normal01')]:
        d=a.root/tag;b=BASE/'probes/nes-ingress338'/ref
        if not (d/'result.json').exists():assert a.partial,tag;continue
        r=js(d/'result.json');br=js(b/'result.json');assert r['passed'] and r['rtl_hashes']==br['rtl_hashes']
        for n,h in r['rtl_hashes'].items():assert sha(d/n)==h;read(d/n)
        for n in ('blocks.txt','CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc'):
            assert sha(d/n)==sha(b/n),(tag,n);pins[str(d/n)]=sha(d/n)
        for n in ('blocks.csv','control.json','decoder.elf','nes_decode280.c'):
            q=a.root/'decoder01'/n;assert sha(d/('source-ARM-'+n))==sha(q);pins[str(q)]=sha(q)
        assert sha(d/'nes_decode280.c')==sha(a.root/'decoder01/nes_decode280.c')
        blocks=list(csv.DictReader(read(d/'source-ARM-blocks.csv').splitlines()))
        costs=[int(x,16) for x in read(d/'source-cost280.hex').split()]
        assert costs==[int(x['instructions']) for x in blocks]
        assert sha(d/'output.elf')==r['ELF_sha256'];pins[str(d/'output.elf')]=sha(d/'output.elf')
        if image is None:image=load_image(d/'output.elf')
        else:assert load_image(d/'output.elf')==image,(tag,'ARM load image')
        assert sha(d/'joint266_tb.sv')==r['tb_sha256'];read(d/'joint266_tb.sv')
        assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log')
        assert 'PASS REFILL267 frames=3' in read(d/'vsim.log')
        ev=list(csv.reader(read(d/'joint-events.csv').splitlines()))
        cycles={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(d/'cycles.csv').splitlines())}
        profile=js(d/'metadata317.json');rows=[]
        for fi,prev in enumerate(base['runs'][ref]['rows']):
            f=prev['frame'];events=[x for x in ev if len(x)>1 and x[1]==str(f)]
            first=lambda n:next(x for x in events if x[0]==n)
            start=first('start319');end=first('frame_done');req=next(x for x in events if x[0]=='firstreq305' and x[2]=='0');accept=next(x for x in events if x[0]=='rom_accept327' and x[2]=='0')
            startms=int(start[2])/1e9;finishms=int(end[2])/1e9;requestms=int(req[-1])/1e9;acceptms=int(accept[-1])/1e9
            if tag=='fixed02':assert startms==prev['start_ms'] and int(start[3])==prev['start_ROM_cycle']
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            baseline_arm=next(x for x in br['ARM']['frames'] if x['frame']==f)
            assert wire(js(d/f'arm{f}.json')['transfers'])==wire(js(b/f'arm{f}.json')['transfers']),(tag,f,'wire')
            assert arm['decoder_excluded']>baseline_arm['decoder_excluded']
            expected=[];actual=[];offset=0;token=None;writes=[];published=0
            for x in events:
                if x[0]=='read336':
                    tok,op,section,pos,off,data,t=map(int,x[2:]);assert off==offset
                    if not offset:token=tok
                    assert token==tok;offset+=1;u=completed_unit(op,section,pos,2)
                    if u:expected.append((tok,int(u[0]),u[1]))
                elif x[0]=='unit336':actual.append(tuple(map(int,x[2:5])))
                elif x[0]=='private336':
                    tok,addr,value,t=map(int,x[2:]);assert tok==token;writes.append(t)
                elif x[0]=='publish336':
                    tok,n,t=map(int,x[2:]);assert tok==token and n==offset and n>0 and all(z<t for z in writes)
                    offset=0;token=None;writes=[];published+=1
            assert expected==actual and offset==0
            credit=max(int(x[2]) for x in events if x[0]=='credits');assert credit<=2
            prep={}
            for n in ('nes_dirty231_material','nes_dirty231_begin','start286'):
                matches=[x for x in profile if x['name']==n];assert len(matches)==3
                x=matches[fi];prep[n]=x['end']['instruction']-x['start']['instruction']
            total=cycles[f]+int(end[3])/1e9
            rows.append(dict(frame=f,total_ms=total,delta_ms=total-prev['total_ms'],gap_ms=total-1000/60,source_ms=cycles[f],start_ms=startms,start_delta_ms=startms-prev['start_ms'],start_ROM_cycle=int(start[3]),request_ms=requestms,request_relative_ms=requestms-startms,request_delta_ms=requestms-prev['first_request_ms'],accept_ms=acceptms,accept_relative_ms=acceptms-startms,post_ROM_ms=finishms-acceptms,post_ROM_delta_ms=finishms-acceptms-prev['post_ROM_ms'],instructions=arm['instructions'],instruction_delta=arm['instructions']-baseline_arm['instructions'],components=arm['components'],baseline_components=baseline_arm['components'],prep_instructions=prep,SPI_bytes=arm['SPI_bytes'],SPI_delta=arm['SPI_bytes']-baseline_arm['SPI_bytes'],max_credit=credit,qualified_units=len(actual),published_chunks=published,wire_exact=True))
        def sizes(p):
            with p.open('rb') as f:
                elf=ELFFile(f);return {n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.bss','.data')}
        sizes_new=sizes(d/'output.elf');sizes_old=sizes(b/'output.elf')
        runs[tag]=dict(rows=rows,sizes=sizes_new,size_delta={n:sizes_new[n]-sizes_old[n] for n in sizes_new},stack=r['ARM']['stack_observed'],baseline_stack=br['ARM']['stack_observed'],IRQ_cases=len(r['ARM']['IRQ_cases']),RTL_exact=True)
    if a.partial:print(json.dumps(runs,indent=2));return
    guards=js(a.root/'guards01/result.json');assert guards['passed']
    for n,h in guards['pins'].items():assert sha(Path(n))==h;pins[n]=h
    decoder_guards=js(a.root/'decoder-guards01/result.json');assert decoder_guards['passed'] and len(decoder_guards['cases'])==77
    decoder_result=js(a.root/'decoder01/result.json');assert decoder_result['passed'] and len(decoder_result['frames'])==71
    for n,h in decoder_guards['pins'].items():assert sha(Path(n))==h;pins[n]=h
    whole=base['whole'];assert whole['comb']==17274
    budget=dict(status='unimplemented budget, not predicted synthesis saving',whole_cap=15253,required_net_deletion=2021,retained_outside=10950,retained_checker_aperture=1159,retained_concurrent_plan=459,source_host_current=3908,source_host_cap=2035,queue_SPI_current=798,queue_SPI_cap=650)
    assert sum(budget[n] for n in ('retained_outside','retained_checker_aperture','retained_concurrent_plan','source_host_cap','queue_SPI_cap'))==15253
    for n in ('nes_raw352.py','probe_nes_raw352.py','check_nes_raw352.py','analyze_nes_raw352.py','probe_nes_rawdecode352.py','check_nes_rawdecode352.py'):read(ROOT/'tools'/n)
    result=dict(stage=352,passed=True,runs=runs,guards=guards,decoder_guards=decoder_guards,whole=whole,whole_delta=dict(LE=0,comb=0,FF=0,RAM_bits=0),comb_deficit=1866,new_MAP=False,unchanged_RTL_MAP_reused=True,budget=budget,scope='Actual M4 instructions at modeled CPI1/84MHz plus live SPI/IRQ/ROM/2slot and retained SNES trace. Not physical timing, full RUN, full65816, FIT or STA.',pins=pins)
    (ROOT/'analysis/raw352-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,warm={k:v['rows'][-1] for k,v in runs.items()},whole=whole,guard_cases=len(guards['cases']),pins=len(pins)),indent=2))
if __name__=='__main__':main()
