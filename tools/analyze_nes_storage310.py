# SPDX-License-Identifier: MIT
"""Whole timing/area ledger for stored credits and deferred consumption."""
import csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile


def main():
    pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    d=BASE/'probes/nes-storage310';prior=js(ROOT/'analysis/ingress307-verification.json');runs={}
    for tag,mode in [('window05','restricted'),('normal01','normal')]:
        q=d/tag;r=js(q/'result.json');assert r['passed']
        for n,h in r['rtl_hashes'].items():assert sha(pin(q/n))==h
        assert sha(pin(q/'output.elf'))==r['ELF_sha256']
        events=list(csv.reader(pin(q/'joint-events.csv').open()))
        src={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(pin(q/'cycles.csv').open())}
        rows=[]
        for f in (905,906,907):
            es=[x for x in events if len(x)>1 and x[1]==str(f)]
            end=next(x for x in es if x[0]=='frame_done');total=src[f]+int(end[3])/1e9
            base=next(x for x in prior[mode] if x['frame']==f)
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            stores=[x for x in es if x[0]=='store310'];replays=[x for x in es if x[0]=='replay310']
            assert len(stores)==len(replays) and len(stores)<=1
            after=[]
            if stores:
                assert int(stores[0][-1])<int(replays[0][-1])<int(end[2])
                after=[x for x in es if x[0]=='consume293' and int(stores[0][-1])<int(x[-1])<int(replays[0][-1])]
                assert after,('no subsequent DMA consumption',mode,f)
            credit=max(int(x[2]) for x in es if x[0]=='credits');assert credit<=4
            rows.append(dict(frame=f,total_ms=total,delta307_ms=total-base['total_ms'],gap_ms=total-1000/60,
                absolute_finish_ms=int(end[2])/1e9,frame_start_ms=int(end[2])/1e9-total,
                instructions=arm['instructions'],instruction_delta=arm['instructions']-base['ARM_instructions'],
                SPI_bytes=arm['SPI_bytes'],max_credit=credit,store_events=stores,replay_events=replays,
                later_DMA_consumptions=len(after)))
        runs[mode]=dict(rows=rows,observed_stack=r['ARM']['stack_observed'])
    board=js(d/'board01/result.json');assert board['passed']
    for name,h in board['actual_inputs'].items():assert sha(pin(d/'board01'/name))==h
    summary=board['summary']
    def metric(label):return int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',summary)[1].replace(',',''))
    whole=dict(LE=metric('Total logic elements'),comb=metric('Total combinational functions'),FF=metric('Dedicated logic registers'),RAM_bits=metric('Total memory bits'))
    def board_alias(text):
        # Existing board-only tile-close output, identical in baseline307.
        return text.replace(' output wire tile_closed267,\n','').replace('reg tiles_closed;assign tile_closed267=tiles_closed;','reg tiles_closed;')
    for name in ('nes_mux260.sv','nes_validator278.sv','nes_queue260.sv','nes_spi270.sv'):
        board_text=pin(d/'board01'/name).read_text()
        live_text=pin(d/'window05'/name).read_text()
        assert board_alias(board_text)==live_text
        assert sha(pin(d/'window05'/name))==sha(pin(d/'normal01'/name))
    assert board_alias(pin(BASE/'probes/nes-ingress307/board03/nes_mux260.sv').read_text())==pin(BASE/'probes/nes-ingress307/window03/nes_mux260.sv').read_text()
    for tag in ('window05','normal01'):
        with (d/tag/'output.elf').open('rb') as f:
            loaded=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']
        if tag=='window05':first=loaded
        else:assert loaded==first
    checks={}
    for tag in ('earlyguards01','guards01','prepguard02','armguard01','credit01','supply01','native01'):
        checks[tag]=js(d/tag/'result.json');assert checks[tag]['passed']
        if 'ELF_sha256' in checks[tag]:assert checks[tag]['ELF_sha256']==sha(d/'window05/output.elf')
    for tag in ('earlyguards01','guards01'):
        for name in ('nes_mux260.sv','nes_validator278.sv'):
            assert sha(pin(d/tag/name))==sha(d/'window05'/name),('guard RTL mismatch',tag,name)
    size=pin(d/'window05/size287.log').read_text().splitlines()[-1].split()
    result=dict(stage=310,passed=True,selected=False,runs=runs,checks=checks,whole_MAP=whole,
        delta307={k:whole[k]-prior['whole_MAP'][k] for k in whole},comb_deficit=whole['comb']-15408,
        ARM_memory=dict(text=int(size[0]),bss=int(size[2]),observed_stack=runs['restricted']['observed_stack']),
        storage=dict(bytes=90,address=[166,255],kind='compressed requirements only',credit='after final storage write',consumption='independent replay before first map manifest'),
        limitations=['Queue four-slot storage/counters and SPI/plan controllers retained; no complete 9-packet byte arena replacement',
            'CPI1/84MHz M4 execution model; ordinary65816 recorded bus timing with physical sequence data rebound, not fresh full CPU execution',
            'Only 905/906/907 live; no whole71/full ARM RUN, FIT/STA or physical60fps'],input_hashes=pins)
    for n in ('nes_storage310.py','probe_nes_live310.py','guard_nes_storage310.py','map_nes_storage310.py','analyze_nes_storage310.py'):pin(ROOT/'tools'/n)
    (ROOT/'analysis/storage310-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(runs=runs,whole_MAP=whole,delta307=result['delta307']),indent=2))
if __name__=='__main__':main()
