"""Replay collector records on both final ARM links with persistent alternating banks."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

from check_ff3_backdrop1046 import captured, layouts
from check_ff3_sd1043 import Machine, fat16, UC_HOOK_CODE, UC_ARM_REG_R2, UC_ARM_REG_SP

def runtime_modes(src, *, page_history=False):
    """Run committed input through the linked runtime up to planner entry."""
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_LR, UC_ARM_REG_PC
    names=('nes_native165','nes_resident211','nes_native_runtime165','nes_plan200')
    rx,rs,rt,plan=layouts(src, names)
    cases=[(0x7d,0,256 if page_history else 2,1),(0x7d,1,1,1),(0x7c,0,1,2)]
    if page_history:
        cases.extend((0x7d,(255^(1<<p))<<1,1+(1<<p),1) for p in range(8))
    cases=[(0x2234,*case) for case in cases]
    if 'dirty_chr' in rx and page_history:
        cases.extend((0x2235,0x7d,group<<1,257+group,1) for group in (0,1,7,8,16,56,63))
    for version, revision, receipt, content, scheduling in cases:
        m=Machine(src,fat16())
        u=m.u
        u.hook_del(m.hooks['nes_runtime165_step'])
        base=0x21000000
        u.mem_map(base,0x20000)
        u.mem_map(0xe0001000,4096)
        session=base
        receiver,resident,callback=base+0x3000,base+0xa000,base+0x1e000
        # Clock and service callbacks return 1. Only the sink's BEGIN exchange
        # is acknowledged by the fixture; the tested ownership decision is ARM code.
        u.mem_write(callback,struct.pack('<HH',0x2001,0x4770))
        def put(addr,fmt,value):
            u.mem_write(addr,struct.pack('<'+fmt,value))
        u.mem_write(m.sym['nes_board_id'],bytes([revision]))
        for field,value in (('receiver',receiver),('resident',resident),('content_epoch',1),
                            ('ticks',callback|1),('service',callback|1),('limit',1000)):
            put(session+rt[field],'I',value)
        m.call('nes_resident211_reset',resident)
        for field,fmt,value in (('epoch','I',1),('displayed','B',1),('active','B',1)):
            put(resident+rs[field],fmt,value)
        if page_history:
            # Eight ordinary source tags per bank, one per physical page.
            put(resident+rs['bg_slots'],'H',8)
            u.mem_write(resident+rs['bg'],struct.pack('<8H',*(p*64 for p in range(8))))
            for bank in range(2):
                put(resident+rs['resident']+bank*144,'B',255)
        else:
            u.mem_write(resident+rs['resident'],b'\x01'*288)
        header=callback+8
        word=(version<<48)|(1<<42)|(1<<36)|(224<<28)|(receipt<<3)
        u.mem_write(header,struct.pack('>HHQ',0xe000,1,word))
        assert m.call('nes_native165_packet',receiver,0,header,12)
        put(receiver+rx['state'],'B',4)
        observed=[]
        def step(u,pc,size,name):
            if name=='nes_resident211_begin':
                observed.append(u.reg_read(UC_ARM_REG_R2))
            elif name=='nes_sink212_begin':
                u.reg_write(UC_ARM_REG_R0,1)
                u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            else:
                observed.append(u.mem_read(session+rt['plan']+plan['bank_history'],1)[0])
                u.reg_write(UC_ARM_REG_PC,0x0807fff1)
        for name in ('nes_resident211_begin','nes_sink212_begin','nes_native_video211_plan'):
            pc=m.sym[name]&~1
            u.hook_add(UC_HOOK_CODE,step,name,pc,pc)
        m.call('nes_runtime165_step',session)
        assert observed==[content,scheduling],(revision,receipt,observed)
        bits=u.mem_read(resident+rs['resident'],288)
        if page_history:
            invalid=(content-1) if version==0x2234 else sum(1<<p for p in range(8) if p*8==receipt>>1)
            assert bits[0]==bits[144]==(255^invalid),(revision,receipt,content,bits[0],bits[144])
        else:
            assert bool(any(bits))==(content==1)
        if receipt:
            # A restored/partly written back bank must not survive a final ACK
            # carrying an unrelated generation, even when CHR stayed stable.
            u.mem_map(m.sym['__stack'],4096)
            pc=m.sym['nes_resident211_commit']&~1
            def final_displayed(u,pc,size,ctx):
                u.mem_write(u.reg_read(UC_ARM_REG_SP),struct.pack('<I',1))
            u.hook_add(UC_HOOK_CODE,final_displayed,None,pc,pc)
            put(resident+rs['prepared'],'B',1)
            assert not m.call('nes_resident211_commit',resident,1,2,0)
        else:
            m.call('nes_resident211_abort',resident)
        assert not any(u.mem_read(resident+rs['resident'],288))
    print('PASS linked runtime CHR receipt selection, bank scheduling, wrong final generation and abort')


def replay(src, records, history, candidate, stride, *, native_colors=False, pages=None, profile=False,
           written_groups=None, instruction_samples=None, touched_tiles=None, board_id=None):
    rx,video,rs=layouts(src)
    m=Machine(src,fat16())
    u=m.u
    u.mem_map(m.sym["__stack"],4096)  # Caller argument space above the test stack.
    base=0x21000000
    u.mem_map(base,0x20000)
    receiver,out,res,lut,writer,header=(base+x for x in (0,0x4000,0xa000,0xe000,0xe100,0xe200))
    def put(at,fmt,*args):u.mem_write(at,struct.pack('<'+fmt,*args))
    def get(at,fmt):return struct.unpack('<'+fmt,u.mem_read(at,struct.calcsize('<'+fmt)))[0]
    put(writer,'HH',0x2001,0x4770)
    colors=struct.unpack('<64H',u.mem_read(m.sym['native_palette165'],128)) if native_colors else range(64)
    put(lut,'64H',*colors)
    stack=[]
    def args(u,pc,size,ctx):
        if stack:u.mem_write(u.reg_read(UC_ARM_REG_SP),struct.pack('<'+'I'*len(stack),*stack))
    for name in ('nes_resident211_begin','nes_resident211_commit'):
        pc=m.sym[name]&~1
        u.hook_add(UC_HOOK_CODE,args,None,pc,pc)
    commands=[]
    def emit(u,pc,size,ctx):
        command=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R2),40))
        _,slot,tag,kind,mask=struct.unpack_from('<HHHBB',command)
        commands.append((kind,slot,command[4:]))
    u.hook_add(UC_HOOK_CODE,emit,None,writer,writer)
    m.call('nes_resident211_reset',res)
    if board_id is not None:
        u.mem_write(m.sym["nes_board_id"], bytes([board_id]))
    banks=[{},{}]
    tile_epoch=Counter()
    bank_versions=[{},{}]
    serializer,wire_input=base+0x11000,base+0x11400
    wire,=layouts(src,('nes_plan200',))
    encoded_lengths={}
    def descriptor_bytes(gen,slot,body):
        key=slot,body
        if key not in encoded_lengths:
            u.mem_write(serializer,bytes(512))
            u.mem_write(wire_input,struct.pack('<HH',gen,slot)+body)
            # One record enters the real linked E9 encoder; packet framing and
            # independent status queries depend on timing and are excluded.
            assert m.call('append',serializer,wire_input)
            assert get(serializer+wire['count'],'B')==1
            encoded_lengths[key]=get(serializer+wire['bytes'],'H')
        return encoded_lengths[key]
    stats=[]
    last_clean=True
    retained_pages=255
    pending_groups=set()
    for i,(frame,geometry) in enumerate(records):
        last_clean &= history[frame]
        if pages is not None:retained_pages &= pages[frame]
        if written_groups is not None:pending_groups.update(written_groups[frame])
        if touched_tiles is not None:tile_epoch.update(touched_tiles[frame])
        if i%stride:continue
        clean=last_clean;last_clean=True
        clean_pages=retained_pages;retained_pages=255
        if pages is not None:assert clean==(clean_pages==255)
        maps,rows,rasters,objects,ex,palette,pixels=geometry
        gen=frame&65535
        u.mem_write(receiver,bytes(0x4000))
        hdr=(0x2234<<48)|(len(maps)//33<<42)|(len(palette)//32<<36)|(224<<28)|(len(objects)<<20)|(len(ex)<<12)|(int(clean and (candidate or pages is not None))<<3)|(len(pixels)//256)
        if pages is not None and candidate:hdr|=clean_pages<<4
        group=None
        if i and len(pending_groups)==1:
            group,=pending_groups
            hdr=(hdr & ((1<<48)-1) & ~0xff8)|(0x2235<<48)|(group<<4)
        pending_groups.clear()
        u.mem_write(header,struct.pack('>HHQ',0xe000,gen,hdr))
        assert m.call('nes_native165_packet',receiver,0,header,12),(frame,'header')
        if 'dirty_chr' in rx:
            dirty=get(receiver+rx['dirty_chr'],'H')
            assert dirty==(256+group if group is not None else 255^clean_pages)
        elif candidate and pages is not None:assert get(receiver+rx['clean_pages'],'B')==clean_pages
        elif candidate:assert bool(get(receiver+rx['chr_unchanged'],'B'))==clean
        kinds={word&16383:1 for word in maps}
        for word in objects:
            tag=(word&8191)|((word>>36)&8192)
            kinds[tag]=kinds.get(tag,0)|2
        for word in ex:kinds[word>>19]=kinds.get(word>>19,0)|1
        tags=sorted(kinds)
        put(receiver+rx['ntiles'],'H',len(tags))
        put(receiver+rx['tiles'],f'{len(tags)}H',*(t|(kinds[t]<<14) for t in tags))
        put(receiver+rx['maps'],f'{len(maps)}H',*maps)
        u.mem_write(receiver+rx['rows'],bytes(rows))
        put(receiver+rx['raster'],'224Q',*rasters)
        put(receiver+rx['objects'],f'{len(objects)}Q',*objects)
        put(receiver+rx['exceptions'],f'{len(ex)}I',*(x&0xffffffff for x in ex))
        u.mem_write(receiver+rx['exception_hi'],sum((v>>32)<<k for k,v in enumerate(ex)).to_bytes(16,'little'))
        u.mem_write(receiver+rx['palette'],bytes(palette))
        if pixels:u.mem_write(receiver+rx['tiles']+1024,bytes(pixels))
        put(receiver+rx['state'],'B',4)
        if not clean:
            if pages is not None and candidate:
                # Independent source range check: discard all old definitions
                # from a modified physical page, on both destination banks.
                for saved in banks:
                    for key,body in list(saved.items()):
                        tag=int.from_bytes(body[:2],'little')
                        modified=(tag>>3)&63==group if group is not None else not clean_pages&(1<<((tag>>6)&7))
                        if modified:del saved[key]
            else:banks=[{},{}]
        stack[:]=[writer|1,0]
        content=(1+(255^clean_pages)) if candidate and pages is not None else (2 if not clean and (candidate or pages is not None) else 1)
        if 'dirty_chr' in rx:content=1+dirty
        assert m.call('nes_resident211_begin',res,1,content,gen)
        stack.clear();commands.clear()
        executed=[0]
        if profile:
            sample=instruction_samples.get(frame) if instruction_samples is not None else None
            def count_instruction(u,pc,size,data):
                executed[0]+=1
                if sample is not None:sample[pc]+=1
            counter=u.hook_add(UC_HOOK_CODE,count_instruction)
        assert m.call('nes_native_video211_plan',receiver,lut,out,res),(frame,'planner',get(out+video['error'],'B'))
        if profile:u.hook_del(counter)
        serial=get(res+rs['serial'],'I');bank=get(res+rs['target'],'B')
        stack[:]=[1]
        assert m.call('nes_resident211_commit',res,serial,gen,bank)
        stack.clear()
        for k,s,cmd in commands:
            key=(int(k==1),s)
            banks[bank][key]=cmd
            if touched_tiles is not None:
                tag=None if k==2 else int.from_bytes(cmd[:2],'little')&511
                bank_versions[bank][key]=(tag,tile_epoch[tag])
        # Only compare visible tile definitions. Invalidated but unused slots
        # may retain different old data in VRAM; they cannot affect this image.
        used=bytes(u.mem_read(res+rs['used'],144))
        visible=[(int(i>=1024),i if i<1024 else i-1024) for i in range(1152) if used[i//8]&(1<<(i%8))]
        values=[banks[bank][key] for key in visible]
        if touched_tiles is not None:
            for key in visible:
                tag,issued_epoch=bank_versions[bank][key]
                assert issued_epoch==tile_epoch[tag],(frame,bank,key,tag,'stale CHR tile')
        image=hashlib.sha256()
        for key,n in [('map',4096),('oam',544),('cgram',512),('hdma',get(out+video['hdma_size'],'H'))]:
            image.update(bytes(u.mem_read(out+video[key],n)))
        # The identity LUT makes every CGRAM lookup observable even when two
        # entries of a real TV palette happen to be visually indistinguishable.
        for e in range(len(palette)//32):
            for entry in range(16):
                assert get(out+video['cgram']+2*(16*e+entry),'H')==colors[palette[32*e+entry]]
                a,c=divmod(entry,4)
                assert get(out+video['cgram']+2*(128+64*e+16*a+c),'H')==colors[palette[32*e+16+entry]]
        if pixels:image.update(bytes(u.mem_read(out,2048)))
        for v in values:image.update(v)
        counts=Counter(k for k,_,_ in commands)
        wire_bytes=sum(descriptor_bytes(gen,slot,cmd) for _,slot,cmd in commands)
        stats.append(dict(f=frame,clean=clean,commands=len(commands),descriptor_bytes=wire_bytes,tile_bytes=16*(counts[0]+counts[2])+32*counts[1],image=image.hexdigest()))
        if profile:stats[-1]['planner_instructions']=executed[0]
    return stats

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ['old','new','log','report']:ap.add_argument(k,type=Path)
    ap.add_argument('--stride',type=int,default=1)
    ap.add_argument('--flash',type=Path,help='64 effective palettes queried from the real raster RTL')
    a=ap.parse_args()
    runtime_modes(a.new)
    history={int(f):v=='1' for f,v in re.findall(r'CHR_HISTORY (\d+) ([01])',a.log.read_text(errors='replace'))}
    frozen=list(captured(a.log))
    assert frozen
    old=replay(a.old,frozen,history,False,a.stride)
    new=replay(a.new,frozen,history,True,a.stride)
    for x,y in zip(old,new,strict=True):assert x['image']==y['image'] and x['f']==y['f'],(x,y)
    result={'frames':len(old),'stride':a.stride,
            **{k+'_firmware_sha256':hashlib.sha256((src/'obj-nes-100/firmware.stm').read_bytes()).hexdigest() for k,src in [('old',a.old),('new',a.new)]},
            'before':old,'after':new}
    if a.flash:
        palettes=[bytes.fromhex(line) for line in a.flash.read_text().splitlines()]
        assert len(palettes)==64 and all(len(p)==32 for p in palettes)
        # Fix geometry while driving the complete palette sequence actually
        # produced by the board, checking ARM CGRAM without a confounding scene change.
        _,geom=frozen[0]
        fixtures=[]
        for f,pal in enumerate(palettes,1):
            maps,rows,raster,obj,ex,old_pal,pixels=geom
            fixtures.append((f,(maps,rows,raster,obj,ex,list(pal)*(len(old_pal)//32),pixels)))
        traces=replay(a.new,fixtures,{f:f>1 for f,_ in fixtures},True,1,native_colors=True)
        assert len({x['image'] for x in traces})>=2
        result['checked_flash_cgram_frames']=len(traces)
    a.report.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS',len(old),'matching plans and resolved visible tiles; sends',sum(x['commands'] for x in old),sum(x['commands'] for x in new),'tile DMA bytes',sum(x['tile_bytes'] for x in old),sum(x['tile_bytes'] for x in new))
