# SPDX-License-Identifier: MIT
"""Run the deployed485 M4 serializer on pinned captures; ACK endpoint is modeled.

No physical timing, IRQ/ROM competition, gameplay-log replay or new firmware.
Bank images independently expand DATA/word/quad packets and verify full tables.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
from bisect import bisect_right
from check_nes_game478 import Machine, encode, sha
from elftools.elf.elffile import ELFFile
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_PC, UC_ARM_REG_LR


class Audit(Machine):
    def __init__(self, src, palette, out):
        self.collect=False;self.exchange=0x0807ffb0;self.sink=0x20003000
        self.images=[{k:bytearray(n) for k,n in [(2,4096),(3,512),(4,544),(5,3418)]} for _ in range(2)]
        self.out=out;self.rows=[];self.packets=[];self.function_counts=Counter()
        super().__init__(src,palette)
        with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
            e=ELFFile(f)
            self.functions=sorted((s['st_value']&~1,s['st_size'],s.name) for s in e.get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']=='STT_FUNC' and s['st_size'])
            for cu in e.get_dwarf_info().iter_CUs():
                for d in cu.iter_DIEs():
                    if d.tag!='DW_TAG_structure_type' or not d.attributes.get('DW_AT_name') or d.attributes['DW_AT_name'].value!=b'nes_native_sink165' or not d.attributes.get('DW_AT_byte_size'):continue
                    self.layout['nes_native_sink165']={'size':d.attributes['DW_AT_byte_size'].value,**{c.attributes['DW_AT_name'].value.decode():c.attributes['DW_AT_data_member_location'].value for c in d.iter_children() if c.tag=='DW_TAG_member'}}
        for k,off in list(self.layout['nes_native_sink165'].items()):
            if not isinstance(off,int):
                assert off[0]==0x23
                value=shift=0
                for b in off[1:]:
                    value|=(b&127)<<shift
                    if b<128:break
                    shift+=7
                self.layout['nes_native_sink165'][k]=value
        self.starts=[x[0] for x in self.functions]

    def hook(self,u,at,size,user):
        if at==self.exchange:
            p=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2)))
            assert len(p)==16+int.from_bytes(p[12:14],'little')
            op,k=p[:2];offset=int.from_bytes(p[10:12],'little');expanded=int.from_bytes(p[14:16],'little');body=p[16:]
            assert int.from_bytes(p[2:4],'little')==len(self.packets)
            self.packets.append(p)
            if op in [2,4,5,8]:
                data=body if op==2 else body*(expanded//len(body))
                assert len(data)==(len(body) if op==2 else expanded)
                assert offset+len(data)<=len(self.images[self.bank][k])
                self.images[self.bank][k][offset:offset+len(data)]=data
            else:assert op==3
            ack=bytes([int(op==3),op])+p[2:10]+b'\x65\x9a'
            u.mem_write(u.reg_read(UC_ARM_REG_R3),ack)
            u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if self.collect and at!=self.end:
            i=bisect_right(self.starts,at)-1
            name=self.functions[i][2] if i>=0 and at<sum(self.functions[i][:2]) else '<unknown>'
            self.function_counts[name]+=1
        super().hook(u,at,size,user)

    def call(self,name,args):
        if name!='nes_resident211_commit':return super().call(name,args)
        r=self.layout['nes_resident211'];v=self.layout['nes_native_video165'];s=self.layout['nes_native_sink165']
        def read(base,layout,key,n):return int.from_bytes(self.u.mem_read(base+layout[key],n),'little')
        self.bank=args[3];self.packets=[];self.function_counts.clear()
        upload=read(self.resident,r,'map_upload',8);changed=read(self.video,v,'map_dirty',8)
        self.u.mem_write(self.sink,bytes(s['size']))
        for key,value,n in [('exchange',self.exchange|1,4),('serial',args[1],4),('generation',args[2],2),('state',1,1),('displayed',read(self.resident,r,'displayed',1),1)]:
            self.u.mem_write(self.sink+s[key],value.to_bytes(n,'little'))
        self.collect=True
        try:ok=super().call('nes_sink212_seal',[self.sink,self.video,self.resident])
        finally:self.collect=False
        assert ok==1,('seal',args[2])
        descriptor=self.packets[-1][16:];assert len(descriptor)==168
        lengths=struct.unpack_from('<6H',descriptor)
        for k,key in [(2,'map'),(3,'cgram'),(4,'oam'),(5,'hdma')]:
            n=lengths[k]
            # Raw patch bundles are laid out separately after hdma[1121].
            if k==5 and n>1121:
                hdmasize=read(self.video,v,'hdma_size',2)
                expected=bytes(self.u.mem_read(self.video+v['hdma'],hdmasize))+bytes(1121-hdmasize)
                expected+=bytes(self.u.mem_read(self.video+v['patch'],2291))+bytes(self.u.mem_read(self.video+v['patch']+2292,6))
                # Struct contains table lengths at its tail; match serialized sections.
                assert len(expected)==n and bytes(self.images[self.bank][k][:n])==expected
            else:assert bytes(self.images[self.bank][k][:n])==bytes(self.u.mem_read(self.video+v[key],n)),(args[2],k)
        counts=Counter();body=Counter();logical=Counter();ops=Counter()
        frame_dir=self.out/f'frame{args[2]}';frame_dir.mkdir()
        for i,p in enumerate(self.packets):
            k='manifest' if p[0]==3 else ['BG','OBJ','map','CGRAM','OAM','HDMA'][p[1]]
            counts[k]+=1;body[k]+=len(p)-16;logical[k]+=len(p)-16 if p[0] in [2,3] else int.from_bytes(p[14:16],'little');ops[str(p[0])]+=1
            (frame_dir/f'packet{i:03}.bin').write_bytes(p)
        row={'frame':args[2],'bank':self.bank,'changed_map_granules':changed.bit_count(),'upload_map_granules':upload.bit_count(),
             'packet_count':len(self.packets),'section_packets':dict(counts),'section_body_B':dict(body),'section_expanded_B':dict(logical),
             'E1_wire_B':sum(len(p)+3 for p in self.packets),'op_counts':dict(ops),'target_instructions':sum(self.function_counts.values()),
             'function_instructions':dict(self.function_counts),'payload_SHA256':hashlib.sha256(b''.join(self.packets)).hexdigest()}
        self.rows.append(row)
        # The real serializer already executed resident commit after modeled final ACK.
        return 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','dataset','reference','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--first',type=int,default=905);p.add_argument('--last',type=int,default=975)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    reference=json.loads((a.reference/'result.json').read_text(encoding='utf8'));assert reference['passed']
    palette=struct.pack('<64H',*map(int,re.search(r'\{(.*?)\}',(a.arm/'nes_palette165.inc').read_text(encoding='utf8'),re.S)[1].split(',')))
    m=Audit(a.arm,palette,a.out);inputs={}
    for serial,frame in enumerate(range(a.first,a.last+1),1):
        paths=[a.dataset/f'frame{frame}.{ext}' for ext in ['geometry','raw']]
        for q in paths:assert sha(q)==reference['input_sha256'][q.name];inputs[q.name]=sha(q)
        geometry,raw=[q.read_bytes() for q in paths];packets,_,_=encode(geometry,raw,frame)
        actual=m.frame(packets,geometry,raw,frame,serial)
        # Full baseline equality is meaningful only for the original905.. sequence.
        if a.first==905:
            prior=json.loads((a.reference/f'frame{frame}.json').read_text(encoding='utf8'))['candidate']
            assert actual['state_sha256']==prior['state_sha256'] and actual['plans']==prior['plans'],frame
        m.rows[-1]['plan_count']=len(actual['plans'])
        print(json.dumps({'frame':frame,**{k:m.rows[-1][k] for k in ['section_body_B','upload_map_granules','target_instructions']}}),flush=True)
    result={'passed':True,'scope':__doc__,'firmware_SHA256':sha(a.arm/'obj-nes-100/firmware.stm'),'inputs':inputs,'frames':m.rows,
            'full_state_and_plans_match':a.first==905,'new_firmware':False,'hardware_time_proven':False}
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
