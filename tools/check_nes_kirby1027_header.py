"""Decode the actual serialized RTL headers with the same reader used for hardware."""
import json
import re
import struct
from pathlib import Path
from read_nes_display1010 import HEADER, ROW
from read_nes_tail1012 import CAPACITY, SIZE, decode

WORK=Path(__file__).resolve().parents[2]/'probes/nes-kirby1027'


def read_case(case):
    log=(WORK/f'case{case}.log').read_text()
    assert f'PASS1026 case={case} ' in log and 'Errors: 0' in log
    raw,=re.findall(r'^# HEADER1027 ([\da-fx]{64})$',log,re.M)
    if case<5:
        assert 'x' not in raw
    # Canceled records can contain don't-care payload bits. Both possible
    # byte values must be rejected by the same footer/identity check.
    data=bytes.fromhex(raw.replace('x','0'))
    oracle=dict((k,int(v)) for k,v in re.findall(r'(\w+)=(\d+)',re.search(r'^# PASS1027 (.+)$',log,re.M)[1]))
    def row(h):
        buf=bytearray(SIZE)
        HEADER.pack_into(buf,0,0x9001,1027,0,1,0,0,ROW.size,CAPACITY)
        desc=struct.pack('<BBHHHI',1,1,96,384,1619,3135)
        ROW.pack_into(buf,HEADER.size,5762,1619,661,2000,2,10,20,0,7,0,h,desc)
        return decode(buf,1027)['rows'][0]
    if case>=5:
        assert 'invalid' in row(data) and 'invalid' in row(bytes.fromhex(raw.replace('x','f')))
        return dict(case=case,rejected=True)
    r=row(data)
    age=r['last_slot_run']['ticks_from_first_E9']
    origin=data[6]|((data[9]&3)<<8)
    for key,field in [('group','plan'),('request','first_request'),('grant','first_grant'),
                      ('done','done'),('end','END'),('head_E8','head_E8')]:
        assert (origin+age[field]-oracle[key])%1024 in (0,1),(key,case,age,oracle)
    assert r['previous_show']==254 and r['show'] in (oracle['head_E8'],oracle['head_E8']+1)
    corrupt=bytearray(data);corrupt[12]^=1
    assert 'invalid' in row(bytes(corrupt))
    no_read=bytearray(data);no_read[9]&=63
    assert not row(bytes(no_read))['last_slot_run']['foreground_read']
    one_read=bytearray(data);one_read[9]&=127
    assert 'unresolved' in row(bytes(one_read))['last_slot_run']
    return dict(case=case,observed_ticks=age,tiles=r['tiles'],chunks=r['chunks'],token=3135)


if __name__=='__main__':
    rows=[read_case(i) for i in range(7)]
    assert rows[1]['observed_ticks']['first_grant']>rows[0]['observed_ticks']['first_grant']
    assert rows[3]['observed_ticks']['done']==rows[0]['observed_ticks']['done']
    assert rows[3]['observed_ticks']['END']>rows[0]['observed_ticks']['END']
    assert rows[4]['observed_ticks']['writer']==rows[0]['observed_ticks']['writer']
    assert rows[4]['observed_ticks']['head_E8']>rows[0]['observed_ticks']['head_E8']
    (WORK/'proof/header.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('PASS 5 causal controls, 2 missing-event guards, token and wrap checks')
