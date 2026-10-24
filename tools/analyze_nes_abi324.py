# SPDX-License-Identifier: MIT
"""Measured319 trace audit; proposed ABI budgets are not implementation results."""
import csv,json
from collections import Counter
from nes_delta231 import BASE,ROOT,sha

def main():
    pins={}
    def text(p):
        pins[str(p)]=sha(p)
        return p.read_text(encoding='utf-8-sig')
    ref=json.loads(text(ROOT/'analysis/owner319-verification.json'))
    rejected=json.loads(text(ROOT/'analysis/units323-verification.json'))
    assert ref['passed'] and rejected['passed']
    rows=[]
    for run in ('fixed02','window01','normal01'):
        for frame in (905,906,907):
            transfers=json.loads(text(BASE/f'probes/nes-owner319/{run}/arm{frame}.json'))['transfers']
            encoded=expanded=n=split=0
            for t in transfers:
                b=bytes.fromhex(t['tx'])
                if not b or b[0]!=0xe1 or b[1] not in (2,4,5,8):continue
                length=int.from_bytes(b[13:15],'little')
                assert len(b)==length+19
                out=length if b[1]==2 else int.from_bytes(b[15:17],'little')
                assert out>0
                encoded+=length;expanded+=out;n+=1
                split+=max(0,(out+239)//240-1)
            rows.append(dict(run=run,frame=frame,ordinary_records=n,encoded_payload=encoded,
                expanded_payload=expanded,literal_extra_payload=expanded-encoded,
                literal_extra_packets_240B=split,literal_extra_E1_overhead=19*split,
                response_credit_ARM_cost_included=False))
    cpu=BASE/'probes/nes-executor313/cpu03'
    timing=list(csv.DictReader(text(cpu/'timing.csv').splitlines()))
    bus=list(csv.DictReader(text(cpu/'bus.csv').splitlines()))
    counts=Counter()
    for x in bus:
        a=int(x['address']);w=int(x['write'])
        if not w and 0x6060<=a<=0x6068:counts['byte_descriptor_reads']+=1
        if not w and 0x6048<=a<=0x604b:counts['token_reads']+=1
        if w and 0x604c<=a<=0x604f:counts['token_writes']+=1
    counts['commands']=len(timing)
    counts['output_bytes']=sum(int(x['output_bytes']) for x in timing)
    counts['service_master_clocks']=sum(int(x['service_clocks']) for x in timing)
    counts['dma_setup_service_master_clocks']=sum(int(x['dma_setup_service_clocks']) for x in timing)
    assert len(timing)==544
    for name in ('nes_mux260.sv','nes_validator278.sv'):
        text(BASE/'probes/nes-owner319/board01'/name)
    text(BASE/'probes/nes-owner319/board01/output_files/board.map.rpt')
    pins[str(ROOT/'tools/analyze_nes_abi324.py')]=sha(ROOT/'tools/analyze_nes_abi324.py')
    out=dict(stage=324,passed=True,kind='existing_trace_and_interface_audit',baseline=319,
        rows=rows,CPU313_trace=dict(counts),CPU_trace_is_separate_not_new_fullpath=True,
        measured_whole=dict(LE=22618,comb=17824,FF=9022,RAM_bits=307808),
        target_comb=15408,regional_comb=6700,regional_target=4284,
        remaining_ms=0.4532188013333318,post_consume_ms=0.236063,
        upstream_minimum_if_terminal_free_ms=0.4532188013333318-0.236063,
        new_ARM_run=False,new_RTL=False,new_Quartus_run=False,
        candidate_comb=None,candidate_time_ms=None,selected_for_production=False,input_hashes=pins)
    (ROOT/'analysis/abi324-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in out.items() if k!='input_hashes'},indent=2))

if __name__=='__main__':main()
