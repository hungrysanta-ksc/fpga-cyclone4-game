# SPDX-License-Identifier: MIT
"""1814 raw steady-state local differences, still bounded by the5000 budget.

Same raw row count uses the last displayed WRAM image/active VRAM bank.
Count transitions, large changes and overflow retain inactive-bank rebuild.
No protocol change, extra frame storage, firmware deployment or FPS claim.
"""
from pathlib import Path
import argparse, inspect, json, shutil
import nes_client181 as client
import nes_sinkpack181 as packed
import nes_native_local165 as local
from nes_clip178 import replace


class RelaxCode(packed.ShortCode):
    """Monotone branch relaxation by emission ordinal; tables rebuild each pass.

Only explicit jump() sites are candidates. A preceding emit(cond,3) is the
existing opposite-condition/JMP idiom. JSR and handwritten branches stay intact.
Every final displacement is checked by Asm.finish; no byte-stream rewriting.
"""
    selected=set()
    latest=None

    def __init__(self,base):
        super().__init__(base)
        self.sites=[];self.last_emit=None
        type(self).latest=self

    def emit(self,*values):
        self.last_emit=(len(self.data),values)
        super().emit(*values)

    def jump(self,label):
        pos=len(self.data);last=self.last_emit
        conditional=(last is not None and last[0]==pos-2 and
                     len(last[1])==2 and last[1][1]==3 and
                     last[1][0] in (0x10,0x30,0x50,0x70,0x90,0xb0,0xd0,0xf0))
        start=pos-2 if conditional else pos
        short=len(self.sites) in type(self).selected
        if short:
            if conditional:del self.data[-2:]
            self.branch(last[1][0]^0x20 if conditional else 0x80,label)
        else:super().jump(label)
        self.sites.append((start,label,short,conditional))

    def next_selection(self):
        selected=set(type(self).selected)
        for i,(start,label,short,conditional) in enumerate(self.sites):
            if short:continue
            target=self.labels[label]-self.base
            # Shrinking this instruction moves a forward target too.
            saved=3 if conditional else 1
            delta=target-(saved if target>start else 0)-(start+2)
            if -128<=delta<=127:selected.add(i)
        return selected


def emit(c,prefix='local165',service=None):
    source=inspect.getsource(local.emit)
    source=replace(source,' # Setup each region; source bank is always SNES WRAM7F.',
        """ # A count transition requires the established bank rebuild. Equal counts
 # do not imply equal content: all sections and raw CHR are compared below.
 lda(0x1240);c.absolute(0xcd,0x1242);cond(0xd0,'budget')
 # Setup each region; source bank is always SNES WRAM7F.""")
    source=replace(source,
        'c.emit(0xa6,0x40);c.absolute(0xbd,0x1000);sta(0x44);c.absolute(0xbd,0x1010);sta(0x46)',
        """c.emit(0xa6,0x40);c.emit(0xe0,12,0);cond(0xd0,'ordinary_size181')
 lda(0x1240);cond(0xf0,'next');imm(2048);sta(0x44);sta(0x46);jump('pointers181')
 label('ordinary_size181');c.absolute(0xbd,0x1000);sta(0x44);c.absolute(0xbd,0x1010);sta(0x46)
 label('pointers181')""")
    source=replace(source,"c.emit(0xc9,12,0);cond(0x90,'region')",
                   "c.emit(0xc9,14,0);cond(0x90,'region')")
    source=replace(source,'lda(0x1028);c.emit(0x18,0x65,0x5a,0x69,96,0);sta(0x5c)',
        """# HDMA points into staged WRAM; its bundle is not copied during vblank.
 # Charge setup96, not its3418 bytes (which include raw CHR counted separately).
 lda(0x40);c.emit(0xc9,10,0);cond(0xd0,'dma_charge181');imm(0);jump('charge181')
 label('dma_charge181');lda(0x5a)
 label('charge181');c.emit(0x18);c.absolute(0x6d,0x1028);c.emit(0x69,96,0);sta(0x5c)""")
    ns=dict(local.__dict__)
    ns.update(LIMITS=client.LIMITS,OFFSETS=(*local.OFFSETS,0x6961),
              DESTS=(*local.DESTS,0x5000),KINDS=(*local.KINDS,0))
    exec(compile(source,'rawsteady181-local','exec'),ns)
    return ns['emit'](c,prefix,service)


def source181(s):
    s=packed.source181(s)
    s=replace(s,'from nes_sinkpack181 import ShortCode as Code',
              'from nes_rawsteady181 import RelaxCode as Code')
    # Intermediate relaxation passes may exceed the compact ROM budget. They
    # are never selected; final build enforces the original3776/4096 limits.
    return replace(s,'assert len(body)<=0xec0, (len(body),0xec0)',
                   'assert len(body)<=0x2000, (len(body),0x2000)')


def build(out):
    out.mkdir(parents=True,exist_ok=False)
    source=inspect.getsource(client.build)
    source=replace(source,'from nes_client181 import emit,call,OFFSETS,LIMITS,emit_upload',
                   'from nes_rawsteady181 import emit;from nes_client181 import call,OFFSETS,LIMITS,emit_upload')
    ns=dict(client.__dict__);ns['source181']=source181
    exec(compile(source,'rawsteady181-build','exec'),ns)
    RelaxCode.selected=set();passes=[]
    for i in range(16):
        d=out/f'pass{i:02}';result=ns['build'](d)
        code=RelaxCode.latest;selection=code.next_selection()
        passes.append(dict(body_bytes=result['body_bytes'],short_jumps=len(RelaxCode.selected)))
        if selection==RelaxCode.selected:break
        RelaxCode.selected=selection
    else:raise AssertionError('branch relaxation did not converge')
    assert result['body_bytes']<=3776
    for p in d.iterdir():
        if p.is_file():shutil.copyfile(p,out/p.name)
    result.update(scope=__doc__,sink_version='1814',seal_version='1814',
                  additional_frame_ram=0,raw_steady=True,relaxation_passes=passes)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


if __name__=='__main__':
    from nes_rawsteady181 import build
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    print(json.dumps(build(p.parse_args().out),indent=2))
