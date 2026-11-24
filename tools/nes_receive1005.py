"""Run checked tile bitmap and literal section-5 receivers inside the 978 two-slot replay."""
import argparse
from pathlib import Path
from build_nes_trace_replay import Code
from nes_credit1004 import execute
from nes_dma1000 import ORIGIN, PACKED, once
from check_nes_plan975 import read


def candidate(mode):
    labels=read(PACKED/'labels.json')
    body=(PACKED/'body.bin').read_bytes()
    c=Code(ORIGIN+len(body))
    patch={}
    def hook(at,original):
        assert body[at-ORIGIN:at-ORIGIN+3]==bytes.fromhex(original)
        dest=c.base+len(c.data)
        patch[at]=bytes((0x4c,dest&255,dest>>8&255))
    def op(code,value):
        c.absolute(code,value&65535)
    def jump(dest):
        op(0x4c,dest)
    if mode in ('tile','both'):
        # At most nine units and bit position <=7 fit a 16-bit mask.
        table=c.base
        for n in range(10):
            c.word((1<<n)-1)
        at=ORIGIN+body.index(bytes.fromhex('29 07 00'),labels['units212']-ORIGIN,labels['bit_ready212']-ORIGIN)
        hook(at,'29 07 00')
        c.emit(0xa6,0x60);op(0xe0,2);c.branch(0xd0,'scalar')
        c.emit(0xa6,0x6c);op(0xe0,2);c.branch(0x90,'scalar')
        op(0xe0,10);c.branch(0xb0,'scalar')
        op(0x29,7);c.emit(0xa8,0x8a,0x0a,0xaa);c.long(0xbf,table)
        op(0xc0,0);c.branch(0xf0,'mask')
        c.label('shift');c.emit(0x0a,0x88);c.branch(0xd0,'shift')
        c.label('mask');c.emit(0x85,0x6e,0xa5,0x6a,0x4a,0x4a,0x4a,0xaa,0x18)
        op(0x6d,0x1254);c.emit(0xa8,0xa5,0x6e)
        op(0xc9,256);c.branch(0xb0,'checkmask');c.emit(0xe2,0x20)
        c.label('checkmask');op(0x3c,0x1280);c.branch(0xd0,'restore16')
        op(0x1d,0x1280);op(0x9d,0x1280);c.emit(0xa5,0x6e)
        op(0x19,0x1320);op(0x99,0x1320);c.emit(0xc2,0x20,0x64,0x6c)
        done=labels['same_byte556']+6
        assert body[done-ORIGIN:done-ORIGIN+2]==bytes.fromhex('a6 60')
        jump(done)
        # Original scalar routine preserves partial-write and fault semantics
        # even when the duplicate is not the first bit in this mask.
        c.label('restore16');c.emit(0xc2,0x20)
        c.label('scalar');c.emit(0xa5,0x6a);op(0x29,7);jump(at+3)
    if mode in ('section','both'):
        at=labels['data']
        hook(at,'ad 01 12')
        op(0xad,0x1200);op(0xc9,0x0502);c.branch(0xd0,'generic')
        op(0xad,0x120a);op(0xc9,1121);c.branch(0x90,'generic')
        # Entry already passed header length, generation, serial and token.
        # This is the dense section; the original mark routine returns SEC
        # immediately for it. Preserve the contiguous cursor and upper bound.
        op(0xcd,0x108a);c.branch(0xd0,'bad')
        op(0xad,0x120c);c.branch(0xf0,'bad');c.emit(0x18);op(0x6d,0x120a)
        c.branch(0xb0,'bad')
        bound=labels['sparse212']-ORIGIN
        cmp_at=body.index(bytes((0xdf,)),bound,bound+45)
        cap=int.from_bytes(body[cmp_at+1:cmp_at+4],'little')+10
        c.long(0xcf,cap);c.branch(0x90,'within');c.branch(0xd0,'bad')
        c.label('within');op(0x8d,0x1234);op(0x8d,0x108a)
        dest=0x3674+10
        assert body[dest-0x2000:dest-0x2000+2]==bytes.fromhex('00 65')
        op(0xad,0x1020);c.emit(0x18);op(0x69,0x6500);op(0x6d,0x120a)
        op(0x8d,0x2181);c.emit(0x85,0x7a,0xe2,0x20);c.store(0x2183,1)
        c.store(0x4304,0x40);c.emit(0xc2,0x20)
        op(0xa9,0x8000);op(0x8d,0x4300);op(0xa9,16);op(0x8d,0x4302)
        op(0xad,0x120c);op(0x8d,0x4305);jump(labels['literal_length227'])
        c.label('generic');op(0xad,0x1201);jump(at+3)
        c.label('bad');jump(0x27af)
    patch[c.base]=c.finish()
    return patch,c.labels


def run(temp,phase,mode,fault):
    patch,labels=candidate(mode)
    base_labels=read(PACKED/'labels.json')
    out=temp/(f'nes-receive1005-{mode}-p{phase}'+('-duplicate-checked' if fault=='duplicate' else '-'+fault if fault else ''))
    def instrument(s):
        anchor='packet=requests[index];sample516("load");'
        writes=';'.join(f'emu.write({a+i-0x7e0000},{v},emu.memType.snesWorkRam)'
                        for a,data in patch.items() for i,v in enumerate(data))
        code=anchor+'if pw(8)==912 and pb(0)==1 then '+writes+' end;'
        if fault=='offset':
            code+="if pw(8)==912 and pb(0)==2 and pw(10)==1322 then packet=packet:sub(1,10)..string.pack('<I2',1323)..packet:sub(13) end;"
        s=once(s,anchor,code)
        hooks={'data':read(PACKED/'labels.json')['data'],'accepted':read(PACKED/'labels.json')['accepted']}
        hooks.update({k:v for k,v in labels.items() if k in ('mask','restore16','within')})
        taps=''.join(f"checkedMem527(function() if packet and pw(8)==912 then sample516('rx1005_{k}') end end,emu.callbackType.exec,{v})\n"
                     for k,v in hooks.items())
        if mode in ('tile','both') and fault:
            table=ORIGIN+len((PACKED/'body.bin').read_bytes())-0x7e0000
            taps+=f'''checkedMem527(function()
 if packet and pw(8)==912 then
  for n=0,9 do assert(word({table}+2*n)==(1<<n)-1,'WRAM mask table') end
 end
end,emu.callbackType.exec,{labels['mask']})
'''
        if fault=='duplicate':
            # This deliberate pre-copy rejection has no successful tile receipt.
            guard="if pb(0)==7 then assert(lastStatus==0 and reads==#tile,'early bulk ACK')end"
            s=once(s,guard,"if pb(0)==7 and pw(8)==912 and pw(16)==35 then assert(lastStatus==224 and reads==0 and #token==0,'invalid duplicate rejection') else "+guard+" end")
            at=base_labels['bit_ready212']-16
            assert (PACKED/'body.bin').read_bytes()[at-ORIGIN:at-ORIGIN+3]==bytes.fromhex('29 07 00')
            taps+=f'''local injected1005=false
checkedMem527(function()
 if not injected1005 and packet and pw(8)==912 and pb(0)==7 and pw(16)==35 then
  local bit=word(0x6a)+word(0x6c)-1
  local a=0x1280+bit//8
  local m=1<<(bit%8)
  assert(rd(a)&m==0)
  emu.write(a,rd(a)|m,emu.memType.snesWorkRam)
  injected1005=true;sample516('rx1005_duplicate',bit)
 end
end,emu.callbackType.exec,{at})
'''
        if fault:
            taps+=f'''checkedMem527(function()
 if packet and pw(8)==912 and pb(0)==2 and pb(1)==5 and pw(10)>=1121 then
  local addr=0x10000+word(0x1020)+0x6500+pw(10)
  for i=0,pw(12)-1 do assert(rd(addr+i)==pb(16+i),'section 5 WRAM') end
  sample516('rx1005_verified',pw(12))
 end
end,emu.callbackType.exec,{base_labels['accepted']})
'''
        return once(s,'local sequence=0;',taps+'local sequence=0;')
    execute(temp,phase,'control','bad_seal' if fault in ('offset','duplicate') else fault,destination=out,observe=instrument)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path);p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('mode',choices=('stock','tile','section','both'))
    p.add_argument('--fault',choices=('offset','duplicate','bad_seal','stop_decode'))
    args=p.parse_args();run(args.temp.resolve(),args.phase,args.mode,args.fault)
