"""Exercise the final linked planner, resolve its actual map words and scroll per scanline."""
import argparse
import struct
from pathlib import Path

from check_ff3_sd1043 import Machine, fat16
from elftools.elf.elffile import ELFFile


def offset(attr):
    value=attr.value
    if isinstance(value,int):return value
    assert value[0]==0x23  # DW_OP_plus_uconst
    return sum((b&127)<<(7*i) for i,b in enumerate(value[1:]))


def layouts(src, requested=('nes_native165','nes_native_video165','nes_resident211')):
    result = {}
    names = set(requested)
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as file:
        for cu in ELFFile(file).get_dwarf_info().iter_CUs():
            for item in cu.iter_DIEs():
                a = item.attributes
                if item.tag != 'DW_TAG_structure_type' or 'DW_AT_name' not in a:
                    continue
                name = a['DW_AT_name'].value.decode()
                if name not in names or name in result or 'DW_AT_byte_size' not in a:
                    continue
                result[name] = {m.attributes['DW_AT_name'].value.decode(): offset(m.attributes['DW_AT_data_member_location'])
                                for m in item.iter_children() if 'DW_AT_name' in m.attributes and 'DW_AT_data_member_location' in m.attributes}
            if names == result.keys():
                return [result[n] for n in requested]
    raise ValueError('missing ELF type information')


def captured(log):
    lines = log.read_text(errors='replace').splitlines()
    for i,line in enumerate(lines):
        if not line.startswith('# GEOMETRY '): continue
        frame,groups,objects,exceptions,palettes,patches=map(int,line.split()[2:])
        fields=[]
        for j,(width,n) in enumerate(((4,groups*33),(2,224),(14,224),(13,objects),(9,exceptions),(2,palettes*32),(2,patches*256))):
            text=lines[i+1+j].removeprefix('#').strip()
            assert len(text)==width*n,(frame,j,len(text))
            fields.append([int(text[k:k+width],16) for k in range(0,len(text),width)])
        yield frame,fields


def check(src, bands, records=(), *, fold_backdrop=False, board=None):
    counts = {}
    rx,video,resident = layouts(src)
    for start,end,geometry in [(a,b,None) for a,b in bands]+[(f,f,data) for f,data in records]:
        m=Machine(src,fat16())
        u=m.u
        if board is not None:
            u.mem_write(m.sym["nes_board_id"], bytes([board]))
        # Extra address space is fixture storage for the public function's arguments.
        base=0x21000000
        u.mem_map(base,0x20000)
        receiver,out,res,lut,writer=(base+k for k in (0,0x4000,0xa000,0xe000,0xe100))
        def put(address,fmt,*values):
            u.mem_write(address,struct.pack('<'+fmt,*values))
        def get(address,fmt):
            return struct.unpack('<'+fmt,u.mem_read(address,struct.calcsize('<'+fmt)))[0]
        put(writer,'HH',0x2001,0x4770)  # stage callback accepts each descriptor
        put(res+resident['write'],'I',writer|1)
        put(res+resident['open'],'B',1)
        put(res+resident['generation'],'H',1)
        put(res+resident['index_head'],'256H',*([65535]*256))
        if start!=end:
            # Retained target previously mapped a visible tile across row 31.
            put(res+resident['displayed'],'B',1)
            put(out+video['valid'],'B',1)
            put(out+video['map']+31*64,'32H',*([0x204d]*32))
        put(receiver+rx['state'],'B',4)
        put(receiver+rx['generation'],'H',1)
        put(receiver+rx['counts'],'6H',33,224,0,0,224,32)
        put(receiver+rx['ntiles'],'H',1)
        put(receiver+rx['tiles'],'H',0x4001)
        put(receiver+rx['maps'],'33H',*([1]*33))
        put(receiver+rx['palette'],'B',15)
        put(lut+15*2,'H',0x2108)
        for y in range(224):
            put(receiver+rx['rows']+y,'B',y%8)
            mask=0 if start<=y<end else 0x1e
            put(receiver+rx['raster']+y*8,'Q',mask<<36)
        if geometry:
            maps,rows,rasters,objects,exceptions,palette,pixels=geometry
            kinds={}
            for word in maps:kinds[word&16383]=1
            for word in objects:
                tag=(word&8191)|((word>>36)&8192)
                kinds[tag]=kinds.get(tag,0)|2
            for word in exceptions:
                tag=word>>19
                kinds[tag]=kinds.get(tag,0)|1
            tags=sorted(kinds)
            put(receiver+rx['counts'],'6H',len(maps),224,len(objects),len(exceptions),224,len(palette))
            put(receiver+rx['ntiles'],'H',len(tags))
            put(receiver+rx['tiles'],f'{len(tags)}H',*(tag|(kinds[tag]<<14) for tag in tags))
            put(receiver+rx['maps'],f'{len(maps)}H',*maps)
            u.mem_write(receiver+rx['rows'],bytes(rows))
            put(receiver+rx['raster'],'224Q',*rasters)
            put(receiver+rx['objects'],f'{len(objects)}Q',*objects)
            put(receiver+rx['exceptions'],f'{len(exceptions)}I',*(v&0xffffffff for v in exceptions))
            hi=sum((v>>32)<<k for k,v in enumerate(exceptions))
            u.mem_write(receiver+rx['exception_hi'],hi.to_bytes(16,'little'))
            u.mem_write(receiver+rx['palette'],bytes(palette))
            put(receiver+rx['patch_count'],'B',len(pixels)//256)
            if pixels:u.mem_write(receiver+rx['tiles']+1024,bytes(pixels))
        ok=m.call('nes_native_video211_plan',receiver,lut,out,res)
        assert ok,(start,end,get(out+video['error'],'B'))
        assert get(out+video['cgram'],'H')==(0x2108 if not geometry or palette[0]==15 else 0)
        if start!=end:assert get(out+video['map_dirty'],'Q')&(1<<31)
        # Decode the actual SNES scroll table independently of the planner's
        # per-row working arrays. The table must terminate after exactly 224 lines.
        table=bytes(u.mem_read(out+video['hdma'],get(out+video['hdma_size'],'H')))
        assert table[-1]==0 and len(table)%5==1
        scanlines=[]
        for lines,x,v in struct.iter_unpack('<BHH',table[:-1]):
            assert 1<=lines<=127
            scanlines.extend([(x,v)]*lines)
        assert len(scanlines)==224
        folded=set()
        if geometry and pixels:
            # patch.chr starts at offset zero of the output union. Decode the
            # eight SNES bitplanes including the raw palette base at index 64.
            chr_data=bytes(u.mem_read(out,2048))
            raw_lines=[y for y,v in enumerate(rasters) if v>>49&1]
            has_blank=any((v>>36)&255==0 and not(v>>49&1) for v in rasters)
            retained=[]
            for i,y in enumerate(raw_lines):
                line=pixels[i*256:(i+1)*256]
                if fold_backdrop and has_blank and all(c==palette[0] for c in line):
                    folded.add(y)
                    continue
                slot=len(retained)
                retained.append(y)
                assert scanlines[y][0]==0 and (scanlines[y][1]+y+1)&255==slot
                for x,nes_color in enumerate(line):
                    pos=(x//8)*64+slot*2
                    color=sum(((chr_data[pos+(plane//2)*16+(plane%2)]>>(7-x%8))&1)<<plane for plane in range(8))
                    assert color==64+nes_color,(start,slot,x,color,nes_color)
            assert get(out+video['patch_count'],'B')==len(retained)
            if retained:
                for bank in range(2):
                    table=bytes(u.mem_read(out+2048+bank*81,81))
                    modes=[]
                    for i in range(0,80,5):
                        n=table[i]
                        if not n:break
                        modes.extend([table[i+1]]*n)
                    assert modes==[3 if y in retained else 0 for y in range(224)]
        for y,(x,v) in enumerate(scanlines):
            assert (x,v)==(get(out+video['hofs']+2*y,'H'),get(out+video['vofs']+2*y,'H'))
            row=((v+y+1)&255)//8
            hidden=(rasters[y]>>36)&255==0 and not (rasters[y]>>49)&1 if geometry else start<=y<end
            hidden=hidden or y in folded
            if geometry and not hidden:continue
            for screen_x in range(256):
                col=((x+screen_x)//8)%64
                pos=(col//32)*1024+row*32+col%32
                tile=get(out+video['map']+pos*2,'H')&1023
                assert (tile==0)==hidden,(y,screen_x,tile)
        if geometry:
            counts[start] = dict(objects=get(out+video['objects'],'B'), raw_lines=len(retained) if pixels else 0)
            print('PASS captured frame',start,'blank rows',sum((v>>36)&255==0 and not (v>>49)&1 for v in rasters))
    print('PASS linked Cortex-M4 planner: blank slot, nonblank BG and backdrop palette at every pixel of',len(bands),'frames')
    return counts


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path)
    p.add_argument('--replay',type=Path)
    args=p.parse_args()
    replay=list(captured(args.replay)) if args.replay else []
    if args.replay:assert replay,'no captured geometry'
    check(args.src,[(0,0),(0,1),(0,81),(15,216),(1,224),(0,224)],replay)
