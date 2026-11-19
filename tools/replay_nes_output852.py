"""Replay dot-zero 849 inputs with the ACK-bound map consumer and both output policies."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from check_nes_game478 import sha, ELFFile
from check_nes_hardware494_termination import member_offset
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0
from nes_raw506 import once
from prepare_nes_map828 import PROBES
from replay_nes_input848 import observe_held_frame
from replay_nes_output822 import MirrorLink
from replay_nes_tile821 import main, joint
from test_nes_sender652 import gates


def monitor(s,clip):
    if clip=='transition':
        s=observe_held_frame(s,924)
    s=once(s,'not c.done and st.frameCount>c.frame','not c.done and st.frameCount==c.frame')
    return once(s,'(pb(0)==2 or pb(0)==4) then','(pb(0)==2 or pb(0)==4 or pb(0)==9) then')


def run(temp,clip,phase,policy,tag,dma):
    root=temp/('nes-trans850-c0' if clip=='transition' else 'nes-comparison851')
    arm=PROBES/'nes-output852/bank/src'
    client=PROBES/'nes-output852'/('client-dma' if dma else 'client-board')
    source=json.loads((root/f'sender-{clip}/sender.json').read_bytes())
    hits=root/f'hits-{clip}/hits.json'
    original=joint.Runtime.__init__
    def init(self,a,link):
        original(self,a,link)
        if policy!='common':
            return
        # This control runs the identical binary and decoder. Model a cache
        # miss by withdrawing both published row masks just before BEGIN.
        with (arm/'obj-nes-100/sd2snes.elf').open('rb') as stream:
            fields={member_offset(m)
                    for cu in ELFFile(stream).get_dwarf_info().iter_CUs()
                    for d in cu.iter_DIEs() if d.tag=='DW_TAG_structure_type' and
                    getattr(d.attributes.get('DW_AT_name'),'value',None)==b'nes_native_sink165'
                    for m in d.iter_children() if getattr(m.attributes.get('DW_AT_name'),'value',None)==b'tail_rows'}
        offset,=fields
        pc=self.syms['nes_sink212_begin']&~1
        def withdraw(u,address,size,ctx):
            u.mem_write(u.reg_read(UC_ARM_REG_R0)+offset,bytes(8))
        self.u.hook_add(UC_HOOK_CODE,withdraw,begin=pc,end=pc)
    budget=Path.home()/'Downloads/nes-budget-mmc826.txt'
    args=['replay','','','','','',tag,str(budget)]
    with patch.object(sys,'argv',args),patch.object(MirrorLink,'lookup_file',hits),gates(source,True),patch.object(joint.Runtime,'__init__',init):
        main(root/clip,clip,'jointmirror',phase,temp,arm=arm,client=client,client_hash=sha(client/'sink165.sfc'),
             link_class=MirrorLink,packet_source=source,adapt_template=lambda s:monitor(s,clip))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path);p.add_argument('clip',choices=('opening','demo','transition'))
    p.add_argument('phase',type=int,choices=(1,2));p.add_argument('policy',choices=('reuse','common'))
    p.add_argument('tag')
    p.add_argument('--dma',action='store_true')
    a=p.parse_args();run(a.temp,a.clip,a.phase,a.policy,a.tag,a.dma)
