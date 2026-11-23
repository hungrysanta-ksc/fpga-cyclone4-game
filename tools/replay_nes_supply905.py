"""Charge each diagnostic SPI page on the linked ARM/65816 replay. ROM stamps
are exercised in the board bench. The ARM fixture uses cache hits for all tiles.
"""
import json
import struct
import sys
from pathlib import Path
from unittest.mock import patch
from replay_nes_tile903 import joint, replay, window, UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR, UC_ARM_REG_PC
from prepare_nes_supply905 import WORK
from read_nes_supply905 import decode,TRACE_BYTES

def run(temp,clip,phase,*,tag='905-supply',out=None,base=None,runner=replay,work=WORK,edition=905):
    out=out or temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{tag}'
    base=base or temp/f'nes-tile821-{clip}-jointmirror-p{phase}-903-tile'
    original=joint.Runtime.__init__
    holders=[];pages=[];commit_steps={};headers=[]
    def stamp(t):return int(t*84000000/joint.MASTER/32768)&1023
    def init(cpu,args,link):
        original(cpu,args,link);holders.append(cpu)
        returns={}
        exch=link.exchange
        def observe(*a):
            lines=exch(*a)
            for item in (lines[3] if len(lines)>3 else '').split(';'):
                if item:
                    tok,t=map(int,item.split(':'));returns[tok]=t
            return lines
        link.exchange=observe
        def frame(u,*_):
            if cpu.generation>=907:u.reg_write(UC_ARM_REG_R0,(5500 if clip=='late' else 3000)+cpu.generation-907)
        def query(u,*_):
            tx=u.reg_read(UC_ARM_REG_R1)
            if u.mem_read(tx,1)!=b'\x78':return
            length=u.reg_read(UC_ARM_REG_R3)
            assert clip=='late' and length in (16,32) and 0x20000000<=tx<0x20010000
            page=u.mem_read(tx+1,1)[0];g=cpu.generation
            if 'finish_header950' in cpu.syms:
                # On 914I tr_gen is sink_spi165.ack_work[79:64]. EA changes
                # plan ownership; D3 and D2 do not write the SNES ACK register.
                last_e0=next(e for e in reversed(cpu.events) if e.get('opcode')=='0xe0')
                status=bytes.fromhex(last_e0['reply'])
                g=int.from_bytes(status[15:17],'little')
                assert status[7:9]==bytes((1,3)) and status[17:19]==bytes((0x65,0x9a))
                if cpu.generation!=g:
                    assert cpu.generation==g+1 and length==16
                    recent=[e for e in cpu.events if e.get('start',-1)>last_e0['clock']]
                    pops=[e for e in recent if e.get('opcode')=='0xd2' and e['input_generation']==g+1]
                    assert pops and recent[-1]['opcode']=='0xd0'
                    assert not any(e.get('opcode') in ('0xe1','0xe9') for e in recent)
                    headers.append(dict(display=g,input=cpu.generation,read=round(cpu.clock),
                                        D2=round(pops[-1]['clock'])))
            assert length==32 or page==0
            if edition in (915,925,950,955,966) and page==0 and 'step_begin915' in cpu.data_symbols and g not in commit_steps:
                def word(name,size):
                    return int.from_bytes(u.mem_read(cpu.data_symbols[name],size),'little')
                assert word('commit_gen915',2)==g
                before=word('step_begin915',4);after=word('commit_clock915',4)
                pops=[e for e in cpu.events if e.get('input_generation')==g and e.get('opcode')=='0xd2']
                edge=int(pops[-1]['clock']*joint.ARM_HZ/joint.MASTER)&0xffffffff
                assert (edge-before)&0xffffffff <= (after-before)&0xffffffff
                commit_steps[g]=dict(before=before,D2=edge,after=after)
            jobs=[j for j in map(json.loads,(out/'producer.jsonl').read_text().splitlines()) if j['generation']==g]
            t0=next(e['start'] for e in cpu.events if e.get('opcode')=='0xe9' and e['generation']==g)
            last=jobs[-1]; count=sum(j['bytes']//(16<<j['kind']) for j in jobs)
            tt=cpu.clock+8*joint.MASTER/2625000
            h=struct.pack('<BBHBBHHHI',0,0x95,g,count,len(jobs),stamp(t0),stamp(tt),stamp(last['producer']),last['token'])
            body=bytearray(16)
            if page>=128:
                for i,j in enumerate(jobs[2*(page-128):2*(page-128)+2]):
                    tok=j['token']
                    v=(tok%2048)<<21|((tok-1)%2)<<20|j['kind']<<19|(j['bytes']//16)<<11|stamp(returns[tok])
                    struct.pack_into('<I',body,8*i,v)
            pages.append((g,page))
            reply=h+bytes(body)
            if edition==927:
                # Bench-proven wire format. Display timings come from Mesen's PPU events.
                assert page==0 and length==32
                reply=bytearray.fromhex((temp/'nes-display927-wire/reply927.hex').read_text())+bytes(8)
                assert reply[1]==0x97 and len(reply)==32
                struct.pack_into('<H',reply,2,g)
            u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(reply[:length]))
            cpu.clock+=length*8*joint.MASTER/2625000+cpu.driver_extra.get(0xe0,0)
            u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        for name,fn in [('nes_budget210_frame',frame),('nes_native165_bulk',query)]:
            at=cpu.syms[name];cpu.u.hook_add(UC_HOOK_CODE,fn,begin=at,end=at)
    with patch.object(joint.Runtime,'__init__',init):
        runner(temp,temp/'nes-latency898',897,clip,phase,candidate_arm=work/'link/src',replay_tag=tag)
    cpu,=holders
    if edition==927:
        from read_nes_display927 import DISPLAYED,decode as decode927
        length=DISPLAYED+4+48+56
    else:
        length=TRACE_BYTES[edition]+2*int(edition==915 and 'step_begin915' in cpu.data_symbols)
    path=out/'records.bin';path.write_bytes(cpu.u.mem_read(cpu.data_symbols['ptrcache'],length))
    data=decode927(path) if edition==927 else decode(path,edition,direct_probe=edition==915 and 'step_begin915' not in cpu.data_symbols)
    if 'finish_header950' in cpu.syms:(out/'headers950.json').write_text(json.dumps(headers))
    if commit_steps:(out/'step915.json').write_text(json.dumps(commit_steps))
    assert len(data['rows'])==(6 if clip=='late' else 0) and not any(data['dropped'])
    assert all('invalid' not in r for r in data['rows'])
    if clip=='late':
        if edition==927:
            assert all('foreground_cycles' in r for r in data['rows'])
            assert any(sum(r['prefetch_cycles']) for r in data['rows'])
            assert any(sum(r['foreground_cycles']) for r in data['rows'])
        else:assert any(r.get('detail') for r in data['rows'])
    def marks(p):
        w={r['g']:r for r in window(p) if r['event']=='reveal'}
        return w[912]['frame']-w[906]['frame']
    for g in range(905,913):assert (out/f'frame-{g}.rgb').read_bytes()==(base/f'frame-{g}.rgb').read_bytes()
    result=dict(pages=len(pages),selected=data.get('selected'),RGB=8,intervals=[marks(base),marks(out)],
                final_ACK=[json.loads((p/'joint.json').read_bytes())['frames'][-1]['ACK_masterclock'] for p in (base,out)])
    (out/'verified905.json').write_text(json.dumps(result))
    print(result)
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
