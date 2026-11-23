"""Timestamp the source fragments, resolved OBJ mask and slot on the released ARM."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP
from nes_ready958 import UC_HOOK_CODE, joint, wire_plan, directory
from nes_tail961 import run

GEN=909
TAG=3074


def observe(temp,phase):
    marks={}
    original=joint.Runtime.__init__

    def attach(cpu,args,link):
        original(cpu,args,link)
        fields=cpu.layout['nes_native165']
        base=cpu.state
        writes={}

        def written(u,access,addr,size,value,user):
            if cpu.generation in (908,909):
                writes.update((a,round(cpu.clock)) for a in range(addr,addr+size))

        for field,length in [('objects',128*8),('raster',224*8),('tiles',512*4)]:
            addr=base+fields[field]
            cpu.u.hook_add(UC_HOOK_MEM_WRITE,written,begin=addr,end=addr+length-1)

        def item(field,index,width):
            addr=base+fields[field]+index*width
            value=int.from_bytes(cpu.u.mem_read(addr,width),'little')
            return value,max((writes.get(a,0) for a in range(addr,addr+width)),default=0)

        def planner(u,pc,size,user):
            if cpu.generation!=GEN:
                return
            assert u.reg_read(UC_ARM_REG_R0)==base
            count,_=item('counts',2,2)
            fragments=[]
            groups={}
            complete=[]
            for i in range(count):
                v,last=item('objects',i,8)
                tag=v&8191
                top=(v>>13)&511
                top=top-512 if top>=256 else top
                mask=(v>>38)&255
                line_masks={}
                raster_writes=[]
                for row in range(8):
                    if not mask&(1<<row):
                        continue
                    y=top+(7-row if v&(1<<37) else row)
                    assert 0<=y<224
                    line,stamp=item('raster',y,8)
                    raster_writes.append(stamp)
                    if line&(1<<40) and not line&(1<<49):
                        epoch=(line>>44)&31
                        line_masks[epoch]=line_masks.get(epoch,0)|(1<<row)
                if tag==TAG:
                    fragments.append(dict(index=i,top=top,raw_mask=mask,rank=(v>>46)&7,
                                          masks=line_masks,object_write=last,raster_write=max(raster_writes)))
                if 255 in line_masks.values():
                    base_tag=tag&~7
                    lanes=groups.setdefault(base_tag,set())
                    if len(lanes)<8:
                        lanes.add(tag)
                        if len(lanes)==8:
                            complete.append(dict(base=base_tag,through_object=i))
            tiles=[item('tiles',i,4) for i in range(item('ntiles',0,2)[0])]
            entry,stamp=next((v,at) for v,at in tiles if v&65535==TAG and (v>>16)&2)
            assert fragments and all(f['object_write'] for f in fragments)
            marks.update(planner=round(cpu.clock),fragments=fragments,tile_kind=(entry>>16)&255,tile_write=stamp,
                         complete_groups=complete,object_count=count)

        def plan(u,pc,size,where):
            if cpu.generation!=GEN:
                return
            addr=(u.reg_read(UC_ARM_REG_R1) if where=='emit' else
                  int.from_bytes(u.mem_read(u.reg_read(UC_ARM_REG_SP),4),'little'))
            q=bytes(u.mem_read(addr,40))
            if int.from_bytes(q[4:6],'little')==TAG and q[6]==1:
                assert int.from_bytes(q[:2],'little')==GEN
                marks.setdefault(where,[]).append([round(cpu.clock),wire_plan(q).hex()])

        pc=cpu.syms['nes_native_video211_plan']
        cpu.u.hook_add(UC_HOOK_CODE,planner,begin=pc,end=pc)
        for name,where in [('nes_resident211_slot','resolve'),('nes_plan200_emit','emit')]:
            pc=cpu.syms[name]
            cpu.u.hook_add(UC_HOOK_CODE,plan,where,begin=pc,end=pc)

    with patch.object(joint.Runtime,'__init__',attach):
        run(temp,phase,'cold',correction='961pair',output_tag='962source')
    d=directory(temp,phase,'962source','cold')
    baseline=directory(temp,phase,'961wirepair','cold')
    for name in ('events.json','window.csv','packets.jsonl','producer.jsonl','e9wire914-909.jsonl'):
        assert (d/name).read_bytes()==(baseline/name).read_bytes(),name
    assert marks['resolve'][0][1][-2:]==marks['emit'][0][1][-2:]=='ff'
    (d/'origin962.json').write_text(json.dumps(marks,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    a=p.parse_args()
    observe(a.temp,a.phase)
