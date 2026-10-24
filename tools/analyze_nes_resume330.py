# SPDX-License-Identifier: MIT
"""Bind ARM-only330 schedules, semantic wires, guards and unchanged325 area."""
import argparse,csv,json
from collections import defaultdict
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');a=ap.parse_args()
    d=BASE/'probes/nes-resume330';pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    old=js(ROOT/'analysis/joint328-verification.json');assert old['passed']
    def wire(transfers):
        g=defaultdict(list)
        for x in transfers:
            b=bytes.fromhex(x['tx'])
            if not b:continue # ARM checkpoint/wait observations have no wire bytes.
            if b[0]==0xe1:g[b[1]].append((b[:3]+b[5:-2]).hex())
            if b[0]==0xe9:g[0xe9].append(b.hex())
        return dict(g)
    runs={}
    for tag,ref in [('window01','arm-window01'),('fixed01','arm-fixed01'),('normal01','arm-normal01'),('tile-window01','arm-window01')]:
        q=d/tag
        if not (q/'result.json').exists():
            assert a.partial,(tag,'missing');continue
        r=js(q/'result.json');assert r['passed'];prev=BASE/'probes/nes-joint328'/ref;pr=js(prev/'result.json')
        assert r['rtl_hashes']==pr['rtl_hashes']
        for n,h in r['rtl_hashes'].items():read(q/n);assert sha(q/n)==h
        assert sha(q/'joint266_tb.sv')==r['tb_sha256'];read(q/'joint266_tb.sv')
        assert sha(q/'output.elf')==r['ELF_sha256'];pins[str(q/'output.elf')]=r['ELF_sha256']
        for n in ('nes_native289.c','nes_output264.c','nes_refill267.c','nes_resume330.py','probe_nes_resume330.py'):read(q/n)
        for n in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
            p=q/('CPU-'+n);assert sha(p)==sha(prev/('CPU-'+n));pins[str(p)]=sha(p)
        events=list(csv.reader(read(q/'joint-events.csv').splitlines()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(q/'cycles.csv').splitlines())}
        metadata=js(q/'metadata317.json');rows=[]
        for prior in old['runs'][ref]['rows']:
            f=prior['frame'];e=[x for x in events if len(x)>1 and x[1]==str(f)]
            def event(name,kind=None):return next(x for x in e if x[0]==name and (kind is None or x[2]==str(kind)))
            start=event('start319');end=event('frame_done');finish=int(end[2])/1e9;total=source[f]+int(end[3])/1e9
            if tag=='fixed01':assert int(start[2])/1e9==prior['start_ms'] and int(start[3])==prior['start_ROM_cycle']
            assert wire(js(q/f'arm{f}.json')['transfers'])==wire(js(prev/f'arm{f}.json')['transfers']),('wire',tag,f)
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            assert sum(int(x[3]) for x in e if x[0]=='arm267')==arm['SPI_bytes']
            credit=max(int(x[2]) for x in e if x[0]=='credits');assert credit<=2
            accept=int(event('rom_accept327',0)[-1])/1e9
            profiles={}
            for name in ('tiles290','bulk289','prepare_map330','issue_map327'):
                calls=[x for x in metadata if x['name']==name and x['start']['generation']==f-904]
                profiles[name]=dict(calls=len(calls),inclusive_instructions=sum(x['end']['instruction']-x['start']['instruction'] for x in calls),
                    first_start_ms=calls[0]['start']['modeled_ns']/1e6 if calls else None,
                    calls_completed_before_ROM=sum(x['end']['modeled_ns']/1e6<accept for x in calls))
            transactions=[x for x in e if x[0]=='arm267']
            command_counts={hex(op):sum(int(x[2])==op for x in transactions) for op in (0xe0,0xe1,0xe2,0xe9,0xea)}
            post=[x for x in transactions if int(x[4])/1e9>=accept]
            tile=[int(x[-1])/1e9 for x in e if x[0]=='consume293' and x[2]=='1']
            map_rows=[int(x[-1])/1e9 for x in e if x[0]=='consume293' and x[2]=='2' and int(x[3])>=128] if f==907 else []
            rows.append(dict(frame=f,start_ms=int(start[2])/1e9,start_ROM_cycle=int(start[3]),finish_ms=finish,total_ms=total,gap_ms=total-1000/60,
                duration_delta_ms=total-prior['total_ms'],finish_delta_ms=finish-prior['finish_ms'],start_delta_ms=int(start[2])/1e9-prior['start_ms'],
                first_ROM_accept_ms=accept,first_BG_ms=int(event('romtile305',0)[-1])/1e9,
                map_manifest_release_ms=int(event('release312',11)[-1])/1e9 if any(x[:3]==['release312',str(f),'11'] for x in e) else None,
                last_tile_consume_ms=tile[-1],first_map_consume_ms=map_rows[0] if map_rows else None,
                last_consume_ms=int([x for x in e if x[0]=='consume293'][-1][-1])/1e9,
                ARM_instructions=arm['instructions'],ARM_delta=arm['instructions']-prior['ARM_instructions'],
                SPI_bytes=arm['SPI_bytes'],SPI_delta=arm['SPI_bytes']-prior['SPI_bytes'],max_credit=credit,
                profiles=profiles,command_counts=command_counts,
                post_ROM_transfer_bytes=sum(int(x[3]) for x in post),
                post_ROM_status_bytes=sum(int(x[3]) for x in post if int(x[2]) in (0xe0,0xe2)),
                opcode_payloads_and_E9_identical=True))
        with (q/'output.elf').open('rb') as f:
            elf=ELFFile(f);sections={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.bss','.data')}
        runs[tag]=dict(rows=rows,SysTick=len(r['ARM']['IRQ_cases']),EXTI=len(r['ARM']['EXTI284']),stack=r['ARM']['stack_observed'],sections=sections)
    if a.partial:
        print(json.dumps(dict(status='partial_not_final',runs=runs),indent=2));return
    def segments(p):
        with p.open('rb') as f:
            return [(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']
    assert segments(d/'window01/output.elf')==segments(d/'fixed01/output.elf')==segments(d/'normal01/output.elf')
    producer=js(d/'producer01/result.json');pause=js(d/'pause01/result.json')
    for result in (producer,pause):assert result['passed'] and result['ELF_sha256']==sha(d/'window01/output.elf') and result['fixture_reads']==0
    assert len(producer['frames'])==71 and len(pause['frames'])==3
    assert producer['script_sha256']==sha(ROOT/'tools/check_nes_resume330.py')
    assert pause['script_sha256']==sha(ROOT/'tools/check_nes_pause330.py')
    guards=js(d/'guards01/result.json');assert guards['passed'] and guards['rtl_hashes']==js(d/'window01/result.json')['rtl_hashes']
    assert guards['ELF_sha256']==sha(d/'window01/output.elf')
    assert guards['tb_sha256']==sha(d/'guards01/joint266_tb.sv');read(d/'guards01/joint266_tb.sv')
    assert sorted(x['case'] for x in guards['cases'])==[3,5,6,7,10,11]
    for case in guards['cases']:
        p=d/'guards01'/f"case{case['case']}"/'vsim.log';raw=read(p);assert sha(p)==case['log_sha256']
        fault=7 if case['case']==10 else 3 if case['case']==6 else 4
        assert f"PASS OWNER319 GUARD={case['case']} fault={fault}" in raw
    aperture=js(d/'guards01/aperture/result.json');assert aperture['passed']
    for n,key in [('nes_bulk_aperture188.sv','RTL_sha256'),('aperture325_tb.sv','tb_sha256'),('vsim.log','log_sha256')]:
        p=d/'guards01/aperture'/n;read(p);assert sha(p)==aperture[key]
    area=js(ROOT/'analysis/budget329-verification.json')
    board=BASE/'probes/nes-expand325/board02/output_files/board.map.rpt';read(board);assert sha(board)==area['pins'][str(board)]
    for n in ('nes_resume330.py','probe_nes_resume330.py','check_nes_resume330.py','check_nes_pause330.py','guard_nes_resume330.py','analyze_nes_resume330.py'):read(ROOT/'tools'/n)
    out=dict(stage=330,passed=True,baseline='325RTL+327ARM verified328',runs=runs,whole=old['ARM_only_whole'],whole_delta=dict(LE=0,comb=0,FF=0,RAM_bits=0),comb_deficit=2394,
        producer_frames=71,producer_guards=producer['guards'],pause_guards=pause['guards'],RTL_guards=guards['cases'],aperture=aperture,
        scope='Actual M4/SPI/IRQ/2slot/ROM + unchanged325 CPU trace; exact325 RTL reuses pinned wholeLite MAP, no new synthesis/physical cycles',
        profile_caveat='Inclusive function counters overlap, include serializer/IRQ and cannot be added as independently removable time.',pins=pins)
    (ROOT/'analysis/resume330-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(passed=True,whole=out['whole'],warm={k:v['rows'][-1] for k,v in runs.items()}),indent=2))

if __name__=='__main__':main()
