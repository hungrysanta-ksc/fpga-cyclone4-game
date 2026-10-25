# SPDX-License-Identifier: MIT
"""Measured partial replacement ledger; never equate it with full NES311 scope."""
import csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile

def main():
    d=BASE/'probes/nes-slots312';pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    prior=js(ROOT/'analysis/ingress307-verification.json');runs={}
    for tag,mode in [('window06','restricted'),('normal01','normal')]:
        q=d/tag;r=js(q/'result.json');assert r['passed']
        for n,h in r['rtl_hashes'].items():assert sha(pin(q/n))==h
        assert sha(pin(q/'output.elf'))==r['ELF_sha256']
        assert sha(pin(q/'joint266_tb.sv'))==r['tb_sha256']
        issues=js(q/'issue307.json');assert issues and all(x['pending']<2 for x in issues),('E1 without storage credit',mode)
        es=list(csv.reader(pin(q/'joint-events.csv').open()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(pin(q/'cycles.csv').open())}
        rows=[]
        for f in (905,906,907):
            ev=[x for x in es if len(x)>1 and x[1]==str(f)]
            end=next(x for x in ev if x[0]=='frame_done');total=source[f]+int(end[3])/1e9
            base=next(x for x in prior[mode] if x['frame']==f)
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            tx=[x for x in ev if x[0]=='arm267']
            assert sum(int(x[3]) for x in tx)==arm['SPI_bytes'],('whole SPI ledger',mode,f)
            responses={hex(cmd):dict(count=sum(int(x[2])==cmd for x in tx),wire_bytes=sum(int(x[3]) for x in tx if int(x[2])==cmd)) for cmd in (224,226,225,233)}
            releases=[x for x in ev if x[0]=='release312' and x[2]=='14']
            receipts=[x for x in ev if x[0]=='receipt312' and x[2]=='14']
            assert len(releases)==len(receipts)
            delays=[(int(b[-1])-int(a[-1]))/1e9 for a,b in zip(releases,receipts)]
            assert all(x>0 for x in delays)
            credit=max(int(x[2]) for x in ev if x[0]=='credits');assert credit<=2
            bg=next(x for x in ev if x[0]=='romtile305' and x[2]=='0')
            finish=int(end[2])/1e9;start=finish-total;grant=int(bg[-1])/1e9
            rows.append(dict(frame=f,total_ms=total,delta307_ms=total-base['total_ms'],gap_ms=total-1000/60,
                start_ms=start,finish_ms=finish,first_BG_ms=grant,before_BG_ms=grant-start,after_BG_ms=finish-grant,
                ARM_instructions=arm['instructions'],instruction_delta307=arm['instructions']-base['ARM_instructions'],
                SPI_bytes=arm['SPI_bytes'],SPI_delta307=arm['SPI_bytes']-base['SPI_bytes'],max_credit=credit,
                responses=responses,batch_release_to_receipt_ms=delays))
        runs[mode]=dict(rows=rows,observed_stack=r['ARM']['stack_observed'])
    board=js(d/'board04/result.json');assert board['passed']
    for n,h in board['actual_inputs'].items():assert sha(pin(d/'board04'/n))==h
    def metric(label):return int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',board['summary'])[1].replace(',',''))
    whole={k:metric(label) for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    def normalize(s):return s.replace(' output wire tile_closed267,\n','').replace('reg tiles_closed;assign tile_closed267=tiles_closed;','reg tiles_closed;')
    for name in ('nes_mux260.sv','nes_queue260.sv','nes_validator278.sv','nes_spi270.sv'):
        assert normalize(pin(d/'board04'/name).read_text())==pin(d/'window06'/name).read_text(),name
        assert sha(pin(d/'normal01'/name))==sha(d/'window06'/name)
    for tag in ('window06','normal01'):
        with (d/tag/'output.elf').open('rb') as f:
            loads=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']
        if tag=='window06':reference=loads
        else:assert loads==reference
    checks={tag:js(d/tag/'result.json') for tag in ('guards03','retained04','armguard02','supply01')}
    assert all(r['passed'] for r in checks.values())
    assert checks['retained04']['positive_control312']
    assert checks['guards03']['queue_sha']==sha(d/'window06/nes_queue260.sv')
    assert checks['guards03']['test_sha']==sha(pin(d/'guards03/queue312_tb.sv'))
    assert checks['retained04']['TB_sha256']==sha(pin(d/'retained04/joint266_tb.sv'))
    for tag in ('armguard02','supply01'):assert checks[tag]['ELF_sha256']==sha(d/'window06/output.elf')
    for name in ('nes_mux260.sv','nes_queue260.sv','nes_validator278.sv','nes_spi270.sv'):
        assert sha(pin(d/'retained04'/name))==sha(d/'window06'/name),('guard source',name)
    host=(d/'window06/nes_mux260.sv').read_text();queue=(d/'window06/nes_queue260.sv').read_text()
    assert 'HCAP:' not in host and 'HREAD:' not in host and 'lengths[' not in queue
    assert 'output reg [191:0] record312' not in queue
    size=pin(d/'window06/size287.log').read_text().splitlines()[-1].split()
    resources={}
    for label,path in [('307',BASE/'probes/nes-ingress307/board03/output_files/board.map.rpt'),('312',d/'board04/output_files/board.map.rpt')]:
        own={}
        for line in pin(path).read_text().splitlines():
            cols=[x.strip() for x in line.split(';')]
            if len(cols)>4 and cols[1] in ('|nes_output260:flow|','|nes_queue260:queue|','|nes_validator278:validator|','|nes_spi270:spi_front270|'):
                own[cols[1]]=dict(comb=int(re.search(r'\((\d+)\)',cols[2])[1]),FF=int(re.search(r'\((\d+)\)',cols[3])[1]))
        assert len(own)==4;resources[label]=own
    r=dict(stage=312,passed=True,implementation_complete=False,selected=False,
        scope='partial canonical admission / two-slot credit gate, NOT complete NES311 record executor',
        runs=runs,whole_MAP=whole,delta307={k:whole[k]-prior['whole_MAP'][k] for k in whole},comb_deficit=whole['comb']-15408,
        ARM_memory=dict(text=int(size[0]),bss=int(size[2]),stack=runs['restricted']['observed_stack']),checks=checks,own_resources=resources,
        deleted=['four-slot raw storage addressing','per-slot packet lengths','host HREAD/HCAP raw header parsing','second queue record snapshot'],
        retained=['ordinary SNES virtual header/body adapter and ACK identity','host batch range parser and completion relays','validator packet/RLE decoder','manifest terminal order','SPI/plan state machines'],
        not_implemented=['canonical expected manifest walker/directory','one common DMA/receipt executor replacing all retained relays','new actual 65816 staging descriptor consumer'],
        limits=['CPI1 actual M4 instructions and IRQ body; ordinary 65816 recorded trace, not new full CPU execution',
                'Only 905/906/907, not full71/heavy7/full ARM RUN/FIT/STA/physical60fps'],input_hashes=pins)
    for n in ('nes_slots312.py','nes_record312.py','probe_nes_live312.py','map_nes_slots312.py','guard_nes_record312.py','guard_nes_slots312.py','guard_nes_credit312.py','analyze_nes_slots312.py'):pin(ROOT/'tools'/n)
    (ROOT/'analysis/slots312-verification.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    print(json.dumps({k:r[k] for k in ('runs','whole_MAP','delta307','comb_deficit','ARM_memory')},indent=2))
if __name__=='__main__':main()
