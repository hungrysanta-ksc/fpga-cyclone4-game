"""Drive the linked ARM recorder with physical MMC955 rows and controlled detail-page replies."""
import json
import struct
from pathlib import Path
from check_nes_frame862_arm import TimedProbe, UC_HOOK_CODE, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from check_nes_game478 import ELFFile
from test_nes_raw506_joint import member_offset
from prepare_nes_dense956 import SOURCE, WORK
from read_nes_supply905 import CAP, ROW, SIZE, decode
from package_nes_trial704 import sha


def check(source):
    assert sha(source)=='1722e64899b5633062d8c2a89768d9ddb519ffe2664bfc416edba232c8ae029e'
    inputs=decode(source,955)
    assert inputs['dropped']==[0,0] and len(inputs['rows'])==120
    original=source.read_bytes()
    q=TimedProbe(SOURCE)
    with (SOURCE/'obj-nes-100/sd2snes.elf').open('rb') as elf:
        plan=next(d for cu in ELFFile(elf).get_dwarf_info().iter_CUs() for d in cu.iter_DIEs()
                  if d.tag=='DW_TAG_structure_type' and 'DW_AT_byte_size' in d.attributes
                  and 'DW_AT_name' in d.attributes and d.attributes['DW_AT_name'].value==b'nes_plan200')
        fields={c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in plan.iter_children() if c.tag=='DW_TAG_member'}
    address=q.rt+q.layout['nes_native_runtime165']['plan']
    tx_pages=[]
    damaged=False
    def spi(cpu,pc,size,_):
        cmd,page=cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),2)
        length=cpu.reg_read(UC_ARM_REG_R3)
        assert cmd==0x78 and length in (16,32)
        packet=bytearray(header)
        if length==32:
            tx_pages.append((gen,page))
            group=page>>7
            values=chunks if group else tiles
            first=(page&127)*2
            packet.extend(b''.join(struct.pack('<Q',v) for v in (values+[0])[first:first+2]))
            assert len(packet)==32
            if damaged and gen==1400 and page==130:packet[12]^=1
        cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2),bytes(packet))
        q.ret(cpu,1)
    pc=q.syms['nes_native165_bulk']
    q.u.hook_add(UC_HOOK_CODE,spi,None,begin=pc,end=pc)
    reports={}
    for damaged in (False,True):
        q.call('nes_budget210_reset',[])
        tx_pages.clear()
        for i,row in enumerate(inputs['rows']):
            tick,gen,bg,ia,ea,_,obj,dirty,_,bank,header,desc=ROW.unpack_from(original,16+i*ROW.size)
            for key,val,width in [('generation',gen,2),('bg_count',bg,2),('obj_count',obj,2),('map_dirty',(1<<dirty)-1,8)]:
                q.put(q.video,'nes_native_video165',key,val,width)
            q.u.mem_write(address+fields['bulk_valid'],bytes([int(bool(desc[0]))]))
            q.u.mem_write(address+fields['bulk'],desc)
            nt,nc=header[4:6]
            if gen in (1396,1400):
                # Synthetic valid detail values for exercising the copies, not measured grants.
                token=int.from_bytes(header[12:16],'little')
                origin=int.from_bytes(header[6:8],'little')
                sizes=[nt-nc+1]+[1]*(nc-1)
                tiles=[(1<<30)|(origin<<20)|(origin<<10)|origin]*nt
                chunks=[]
                for j,n in enumerate(sizes):
                    tok=token-nc+j+1;kind=int(j>0)
                    chunks.append((tok%2048<<21)|((tok-1)%2<<20)|(kind<<19)|(n<<kind<<11)|origin)
            now=(i+2)*9000000
            for name,clock,args in [('input900',now-ia*512,[gen]),('e0900',now-ea*512,[gen,bank])]:
                q.u.mem_write(0xe0001004,struct.pack('<I',clock));q.call(name,args)
            q.u.mem_write(0xe0001004,struct.pack('<I',now))
            q.call('nes_budget210_frame',[tick]);q.call('nes_budget210_display',[tick,q.video])
            q.call('finish_header950',[])
        output=WORK/('damaged.bin' if damaged else 'pair.bin')
        output.write_bytes(bytes(q.u.mem_read(q.data['ptrcache'],SIZE+8)))
        captured=decode(output,956)
        chosen=[r for r in captured['rows'] if 'detail' in r]
        assert not any('invalid' in r for r in captured['rows'])
        assert [r['generation'] for r in chosen]==([1396] if damaged else [1396,1400])
        assert {g for g,_ in tx_pages}=={1396,1400}
        for r in chosen:
            assert sum(c['ROM_grants'] for c in r['detail'])==r['tiles']
            prev=next(old for old in inputs['rows'] if old['generation']==r['generation']-1)
            prev_index=inputs['rows'].index(prev)
            prev_age=ROW.unpack_from(original,16+prev_index*ROW.size)[4]
            age=ROW.unpack_from(original,16+(prev_index+1)*ROW.size)[4]
            expected=((9000000+(prev_age-age)*512)>>9)*512/84000
            assert abs(expected-r['previous_to_current_ARM_ACK_ms'])<=.001
        reports['bad_second_token' if damaged else 'both']=dict(selected=captured['selected'],
            generations=[r['generation'] for r in chosen],detail_page_reads=len(tx_pages))
    return reports


if __name__=='__main__':
    data=check(Path.home()/'Downloads/nes-frame-mmc955.bin')
    (WORK/'pair-proof.json').write_text(json.dumps(data,indent=2)+'\n')
    print(data)
