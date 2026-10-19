# SPDX-License-Identifier: MIT
"""Verify the selected logical RTL/65816 slice and publish payload-free evidence."""
from pathlib import Path
import argparse,csv,json,re
from nes_delta231 import BASE,ROOT,sha


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    td=BASE/'probes/nes-slice257/test06';md=BASE/'probes/nes-slice257/map03';pins={}
    def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
    result=json.loads(pin(td/'result.json').read_text());mapped=json.loads(pin(md/'result.json').read_text())
    assert result['passed'] and result['guards']==list(range(1,10)) and mapped['passed']
    for n,h in result['rtl_hashes'].items():assert sha(pin(td/n))==h
    for n,h in mapped['rtl_hashes'].items():assert h==result['rtl_hashes'][n] and sha(pin(md/n))==h
    for n,h in result['input_hashes'].items():assert sha(pin(BASE/n))==h
    # Recheck source SPI against the older independent source fixture.
    flat=bytearray()
    for line in pin(td/'blocks.txt').read_text().splitlines():
        frame,token,n,b=line.split();data=bytes.fromhex(b);assert frame=='905' and len(data)==int(n);flat+=data
    old=BASE/'probes/nes-joint249/blocktest03'
    size=int(pin(old/'frame905.meta').read_text().split()[0])
    assert flat==bytes.fromhex(pin(old/'frame905.expected.hex').read_text())[:size]
    events=dict((n,int(t)) for n,t in csv.reader(pin(td/'events.csv').read_text().splitlines()))
    assert list(events)==['input_done','staged','dma_done_range','receipt','sealed','display_ack']
    assert list(events.values())==sorted(events.values()) and len(set(events.values()))==6
    rows=[list(map(int,r)) for r in csv.reader(pin(td/'cpu-bus.csv').read_text().splitlines())]
    reads=[r for r in rows if r[1]==0 and 0x400800<=r[2]<=0x400fff]
    assert [r[2] for r in reads]==list(range(0x400800,0x400840))
    expected=bytes.fromhex(pin(td/'selected.hex').read_text())
    assert bytes(r[3] for r in reads)==expected and len(expected)==64
    assert all(b[4]-a[4]==8 for a,b in zip(reads,reads[1:]))
    cpu=json.loads(pin(td/'cpu-result.json').read_text());assert cpu==result['cpu'] and cpu['passed']
    for n in ['vsim.log','vlog.log','capture.lua','rpc.do','slice257_tb.sv','cycles.csv','stream-cycles.csv','output-cycles.csv']:
        pin(td/n)
    faults=[]
    for case in range(1,10):
        log=pin(td/f'guard{case:02}/vsim.log').read_text(errors='replace')
        assert not re.search(r'\*\* (Error|Fatal):',log)
        m=re.search(rf'PASS SLICE257 GUARD {case} fault=(\d+)',log);assert m;faults.append(int(m[1]))
        pin(td/f'guard{case:02}/guard.do')
    for n in ['map.log','output_files/range.map.rpt','output_files/range.map.summary']:pin(md/n)
    # MAP is inclusive; ordinary ACK inputs are tied off and optimized out.
    summary=mapped['summary']
    area={}
    for name,label in [('logic_elements','Total logic elements'),('comb','Total combinational functions'),('registers','Dedicated logic registers'),('memory_bits','Total memory bits')]:
        area[name]=int(re.search(label+r'\s*:\s*([\d,]+)',summary)[1].replace(',',''))
    assert area==dict(logic_elements=1947,comb=1068,registers=1098,memory_bits=40960)
    public=dict(passed=True,stage='R1_first_slice_complete_full_R1_open',selected=dict(test='test06',map='map03'),
        scope='frame905 bank0 map words0..31; actual collector/source/SPI, output packet/queue/parser/aperture, Mesen65816 DMA/VRAM, receipt/seal/display ACK',
        source=dict(canonical_bytes=4398,SPI_payload_bytes=len(flat)),cpu=cpu,rom_body_bytes=result['rom_body_bytes'],
        events_NES_ticks=events,DMA_reads=dict(bytes=64,first_master=reads[0][4],last_master=reads[-1][4],stride_master=8),
        timing=dict(domain_relation='logical RPC, host bus 200ns active +200ns release; poll-zero advances RTL100us; no common physical timeline',
            DMA_start_to_consume_master=cpu['consume_master']-cpu['dma_start_master'],
            DMA_range_to_receipt_NES_ticks=events['receipt']-events['dma_done_range'],whole_frame_bound_ms=None,sixty_fps=False),
        guards=[dict(case=i+1,fault=f,description=s) for i,(f,s) in enumerate(zip(faults,[
            'consume without DMA reads','wrong consume token after64 reads','final ACK before DMA/receipt/seal',
            'STOP after8 DMA reads','display generation mismatch after input release','duplicate consume after receipt',
            'bad E1 packet CRC','packet generation mismatch','packet bank mismatch']))],
        area=dict(**area,tool='Quartus25.1std Lite Build1129',inclusive=True,incremental_cost=None,
            ordinary_ACK_pruned=True,source_core_and_lease_outside_MAP=True,whole_fit=False,STA=False,
            RAM_inferred='1024x8 queue +4096x8 aperture, both M9K; no placement proof',
            local_top_comb=481,local_top_FF=460,mailboxes_comb=25,mailboxes_FF=174,
            warnings='async_reg unrecognized including retained206; reset-loop index j latch warning; six constant range_count pins'),
        limitations=['other90 ranges/8224 bytes and H2/manifest are255 fixtures, not new SPI/SNES path',
            'diagnostic180B consumer body; actual bank register write and VRAM verified, not full rendered game image',
            'single identity/range/session only; ordinary head arbitration, multi-bank/restart/token freshness, tile aperture sharing remain open',
            'collector released, but next capture overlap not exercised',
            'full ARM serializer/RUN/IRQ, heavy7/71frames, board CDC/IO/STA, physical60fps remain open'],
        history=dict(test01='compile declarations/syntax failure',test02='Tcl radix bus error and CPU timeout',
            test03='normal logical coupling PASS',test04='normal RTL PASS, final RPC non-atomic reply race',
            test05='normal + guards1..4 PASS; guard5 found uncleared display lease',
            test06='common STOP includes core fault; normal +all9 PASS',
            map01='Standard evaluation expired before synthesis in sandbox',map02='same expiry before synthesis on host',map03='one actual MAP with installed Lite'),
        rtl_hashes=result['rtl_hashes'],provenance=pins)
    (d/'verification.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(source_bytes=len(flat),guards=9,area=area,events=events)))


if __name__=='__main__':main()
