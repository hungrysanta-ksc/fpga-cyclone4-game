"""Replay mapper-resolved PPU fetches and actual tile demand against a bounded capture cache."""
import argparse
from collections import Counter, defaultdict
import csv
from itertools import groupby
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess

from test_nes_service509_schedule import Calendar
from analyze_nes_scroll229 import FETCH, records
from analyze_nes_wire600 import first_visible_switch, MASTER
from check_nes_wire600 import ROOT, pin, read, sha

FRAMES=range(905,958)
BLOCK='nes_chr_snoop601'
BENCH=BLOCK+'_tb'

def demand(g,plans,packets,chr_rom):
    # SNES receipt order includes the actual ordering of compact OBJ sub-batches.
    slots={}
    for _,h in plans:
        b=bytes.fromhex(h)
        gen,slot,tag,kind,mask=struct.unpack_from('<HHHBB',b)
        assert gen==g and kind in (0,1,2) and tag<8192
        key=(int(kind==1),slot)
        assert key not in slots
        slots[key]=b
    reads=[]
    for b,payload in packets:
        kind=b[1];width=32 if kind else 16
        dest=int.from_bytes(b[10:12],'little')
        assert dest%width==len(payload)%width==0 and int.from_bytes(b[14:16],'little')==len(payload)
        for i in range(0,len(payload),width):
            q=slots.pop((kind,(dest+i)//width))
            gen,slot,tag,k,mask=struct.unpack_from('<HHHBB',q)
            alt=struct.unpack_from('<8H',q,24)
            for j,value in enumerate(payload[i:i+width]):
                if k==2 or j>=16 or not mask>>(j//2)&1:
                    assert value==0
                    continue
                plane_tag=alt[j//2] if not j%2 and alt[j//2]!=65535 else tag
                row=q[8+j]
                assert row<8 and plane_tag<8192
                addr=16*plane_tag+8*(j%2)+row
                assert chr_rom[addr]==value
                reads.append((kind,addr,value))
    assert not slots
    return reads

class Lines:
    def __init__(self,split,count):
        self.split=split
        self.count=count
        self.lines={}
    def line(self,kind,addr):
        return (kind if self.split else 0,(addr//16)%self.count)
    def write(self,kind,addr,value):
        key=self.line(kind,addr)
        if key not in self.lines or self.lines[key][0]!=addr//16:
            self.lines[key]=(addr//16,{})
        self.lines[key][1][addr%16]=value
    def hit(self,kind,addr,value):
        tag,lanes=self.lines.get(self.line(kind,addr),(-1,{}))
        if tag!=addr//16 or addr%16 not in lanes:return False
        assert lanes[addr%16]==value
        return True

def trace_inputs(a):
    old=read(ROOT/'analysis/whole580-verification.json')
    packets={};rom={}
    for ph in old['phases']:
        i=ph['phase'];d=a.traces/f'nes-close561-run{i}'
        for key in ('packets.jsonl','obj-phases.json','window.csv'):
            pin(d/key,ph['evidence'][key])
        with (d/'window.csv').open() as f:
            ack=[int(r['g']) for r in csv.DictReader(f) if r['event']=='ack' and r['op']=='3' and r['value']=='1']
        assert ack==list(FRAMES)
        pk=defaultdict(list)
        for line in (d/'packets.jsonl').read_text().splitlines():
            _,_,h,tile=json.loads(line);b=bytes.fromhex(h)
            if b[0]==7:pk[int.from_bytes(b[8:10],'little')].append((b,bytes.fromhex(tile)))
        packets[i]=pk;rom[i]=read(d/'obj-phases.json')
    return packets,rom

def samples(rows,stim,chr_rom):
    fetched={};maps=defaultdict(set)
    for _,y,d,logical,value,physical,k,*rest in rows:
        if not 7<=y<232 or d%8 not in (5,7):continue
        assert k==57 and chr_rom[physical]==value
        obj=257<=d<=320
        tick=y*341+d+1+(2 if obj and logical&8 else 0)
        fetched[tick,logical,physical]=(obj,value)
    last=-2;seen=[]
    for t,h in enumerate(stim.read_bytes().splitlines()):
        w=int(h,16)
        if w>>54&3!=3:continue
        plane=w>>49&15
        assert plane in (1,2,4,8) and t>=last+2
        addr=w&131071;logical=w>>17&16383
        obj,v=fetched[t,logical,addr]
        assert obj==(plane>2)
        seen.append((int(obj),addr,v))
        maps[logical].add(addr)
        last=t
    return seen,maps

def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False)
    pin(a.rom,read(ROOT/'analysis/trial577-package.json')['required_ROM']['sha256'])
    nes=a.rom.read_bytes()
    assert nes[:4]==b'NES\x1a' and (nes[6]>>4 | nes[7]&240)==4 and not nes[6]&4
    chr_rom=nes[16+16384*nes[4]:]
    assert len(chr_rom)==8192*nes[5]==131072
    s=a.geometry/'stim05';c=a.geometry/'capture02'
    pin(s/'result.json',read(ROOT/'analysis/geometry230-verification.json')['stimulus_result_sha256'])
    stim=read(s/'result.json')
    fetch=c/'ppu-fetch.bin';pin(fetch,stim['inputs'][fetch.name])
    board=read(ROOT/'analysis/whole580-manifest.json')['FPGA_inputs']
    files=('nes_tile205.sv','nes_chr_cache192.sv','nes_direct206.sv','nes_source_tile192.sv','nes_source_epoch207.sv','nes_live_joint.sv')
    for f in files:pin(a.board/f,board[f]['sha256'])
    packets,rom=trace_inputs(a)
    prior=read(ROOT/'analysis/wire600-verification.json')
    history=set();past_fetch=set();previous=set();previous_fetch=set()
    result=[];by_frame={r['frame']:r for r in stim['frames']}
    totals=Counter()
    one_line=Lines(False,1)
    with (a.out/'stim.tsv').open('w',encoding='ascii',newline='\n') as fixture:
        for g,it in groupby(records(fetch,FETCH),key=lambda row:row[0]):
            if g not in FRAMES:continue
            sf=s/f'frame{g}.hex';pin(sf,by_frame[g]['stimulus_sha256'])
            supplied,mappings=samples(it,sf,chr_rom)
            plans=a.plans/f'frame{g}/plans.json'
            primary=demand(g,read(plans),packets[1][g],chr_rom)
            secondary=demand(g,read(plans),packets[2][g],chr_rom)
            assert primary==secondary
            split=Lines(True,128);shared=Lines(False,256)
            # Conservative cold-per-frame comparison, with equal aggregate data capacity.
            fixture.write('0 0 0 0 0\n')
            for k,addr,v in supplied:
                split.write(k,addr,v);shared.write(k,addr,v)
                fixture.write(f'1 {k} {addr:x} {v:x} 0\n')
            misses=shared_misses=old_hits=0
            for k,addr,v in primary:
                ok=split.hit(k,addr,v);misses+=not ok
                shared_misses+=not shared.hit(k,addr,v)
                if one_line.hit(k,addr,v):old_hits+=1
                else:one_line.write(k,addr,v)
                fixture.write(f'2 {k} {addr:x} {v:x} {int(ok)}\n')
            fset={addr for _,addr,_ in supplied}
            address=[addr for _,addr,_ in primary]
            row=dict(generation=g,reads=len(address),distinct=len(set(address)),cold_split_misses=misses,
                     equal_capacity_unified_misses=shared_misses,existing_single_line_hits=old_hits,
                     previous_display_bytes=sum(x in previous for x in address),
                     any_prior_display_bytes=sum(x in history for x in address),
                     previous_capture_bytes=sum(x in previous_fetch for x in address),
                     any_prior_capture_bytes=sum(x in past_fetch for x in address),
                     current_capture_bytes=sum(x in fset for x in address),
                     logical_bytes_with_multiple_physical_addresses=sum(len(v)>1 for v in mappings.values()),
                     samples=len(supplied),plan_sha256=sha(plans))
            totals.update(frames=1,queries=len(primary),hits=len(primary)-misses,fills=len(supplied))
            if g in (952,954):
                row['phases']=[]
                for i in (1,2):
                    base=next(r for r in prior['phases'] if (r['phase'],r['generation'])==(i,g))
                    service=rom[i][str(g)]['rom_service']
                    assert [r[0] for r in service]==[k for k,_,_ in primary] and not misses
                    sc=base['relaxed_calendar'];bus=sc['pre_display_bus_end']
                    reveal=first_visible_switch(bus)
                    row['phases'].append(dict(phase=i,wire_ms=base['wire_floor_ms'],
                        baseline_relaxed_interval_ms=sc['interval_ms'],
                        all_hit_relaxed_interval_ms=(reveal-sc['previous_reveal'])*1000/MASTER,
                        VBlank_wait_after_bus_ms=(reveal-bus)*1000/MASTER,
                        previous_display_miss_shortfall=len(primary)-row['previous_display_bytes']-sc['ROM_grants_from_source_before_deadline']))
            result.append(row);history.update(address);past_fetch.update(fset)
            previous=set(address);previous_fetch=fset
    assert [r['generation'] for r in result]==list(FRAMES)
    report=dict(stage=601,rows=result,totals=dict(totals),source_hashes={f:board[f]['sha256'] for f in files},
                fetch_hash=sha(fetch),fixture_sha256=sha(a.out/'stim.tsv'),physical=False)
    (a.out/'trace.json').write_text(json.dumps(report,indent=2)+'\n')
    print(dict(totals))

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    src=ROOT/'rtl'/(BLOCK+'.sv')
    shutil.copy(src,a.out)
    def execute(args,name):
        with (a.out/(name+'.log')).open('wb') as f:
            subprocess.run(args,cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300,check=True)
    if a.mode=='sim':
        shutil.copy(ROOT/'tools'/(BENCH+'.sv'),a.out)
        trace=read(a.prepared/'trace.json')
        pin(a.prepared/'stim.tsv',trace['fixture_sha256'])
        shutil.copy(a.prepared/'stim.tsv',a.out)
        execute([a.bin/'vlib.exe','work'],'lib')
        execute([a.bin/'vlog.exe','-sv',src.name,BENCH+'.sv'],'compile')
        execute([a.bin/'vsim.exe','-c',BENCH,'-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],'vsim')
        t=trace['totals']
        assert ('PASS601 frames={frames} fills={fills} queries={queries} hits={hits}'.format(**t)
                in (a.out/'vsim.log').read_text())
        result=dict(t,RTL=sha(src),testbench=sha(ROOT/'tools'/(BENCH+'.sv')))
    else:
        (a.out/'region.qpf').write_text('PROJECT_REVISION = "region"\n')
        (a.out/'region.qsf').write_text(f'''set_global_assignment -name FAMILY "Cyclone IV E"
set_global_assignment -name DEVICE EP4CE15F17C8
set_global_assignment -name TOP_LEVEL_ENTITY {BLOCK}
set_global_assignment -name SYSTEMVERILOG_FILE {src.name}
''')
        execute([a.bin/'quartus_map.exe','region'],'map')
        summary=(a.out/'region.map.summary').read_text()
        assert 'Successful' in summary and 'Lite Edition' in summary
        result={k:int(re.search(r'^\s*'+label+r'\s*:\s*([\d,]+)',summary,re.M)[1].replace(',',''))
                for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),
                                ('FF','Dedicated logic registers'),('bits','Total memory bits')]}
        result.update(RTL=sha(src),report=sha(a.out/'region.map.rpt'))
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)

def summarize(a):
    report=read(a.prepared/'trace.json')
    sim=read(a.simulation/'result.json')
    mapped=read(a.mapped/'result.json')
    pin(a.simulation/'stim.tsv',report['fixture_sha256'])
    pin(ROOT/'rtl'/(BLOCK+'.sv'),mapped['RTL'])
    pin(ROOT/'tools'/(BENCH+'.sv'),sim['testbench'])
    pin(a.mapped/'region.map.rpt',mapped['report'])
    assert mapped['RTL']==sim['RTL'] and all(sim[k]==v for k,v in report['totals'].items())
    schedule=read(ROOT/'analysis/wire600-verification.json')['phases']
    control=read(ROOT/'analysis/whole580-verification.json')['phases']
    calendar=Calendar(a.calendar)
    for row in report['rows']:
        for phase in row.get('phases',[]):
            i=phase['phase']; g=row['generation']
            old=next(r for r in schedule if (r['phase'],r['generation'])==(i,g))['relaxed_calendar']
            run=next(r for r in control if r['phase']==i)
            assert run['parameters']['ROM_calendar']==calendar.summary
            shift=run['parameters']['ROM_phase']
            times=a.traces/f'nes-close561-run{i}'/'obj-phases.json'
            pin(times,run['evidence']['obj-phases.json'])
            ea=read(times)[str(g-1)]['ea']
            start=old['source_begin']
            assert ea==start
            # Count all physical opportunities, even if the prior owner needs them.
            def slots(t):
                n=0
                while t<start:
                    t=calendar.select(t-shift)[1]+shift
                    n+=int(t<=start)
                return n
            phase['previous_ACK_to_source_grants_before_ownership_release']=slots(old['previous_ACK'])
            phase['previous_EA_to_source_grants']=slots(ea)
            phase['previous_display_miss_shortfall']=max(0,phase['previous_display_miss_shortfall'])
            phase['bus_end_after_previous_reveal_ms']=(old['pre_display_bus_end']-old['previous_reveal'])*1000/MASTER
    report.update(standalone_map=mapped,simulation=sim,vsim_log_sha256=sha(a.simulation/'vsim.log'),
                  baseline_timing_sha256=sha(ROOT/'analysis/wire600-verification.json'),
                  whole_board_FIT=None,end_to_end_ACK=None,selected=False)
    a.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(report['totals'],mapped)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('prepare','sim','map','summarize'))
    for k in ('out','prepared','geometry','plans','traces','board','rom','bin','simulation','mapped','calendar'):
        p.add_argument('--'+k,type=Path,required=k=='out')
    a=p.parse_args()
    a.out=a.out.resolve()
    {'prepare':prepare,'sim':run,'map':run,'summarize':summarize}[a.mode](a)
