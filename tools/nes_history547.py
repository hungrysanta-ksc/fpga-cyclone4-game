# SPDX-License-Identifier: MIT
"""Exact inactive-bank raw-row comparison after SEAL, before the first blank."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_header546
import nes_rawsteady181
import nes_seal538
from nes_native_local165 import call
from nes_raw506 import once

original_group = nes_seal538.group_upload
original_raw = nes_seal538.raw_service_inline
original_absolute = nes_rawsteady181.RelaxCode.absolute


base_packet = nes_header546.base_packet

def packet(source):
    source=base_packet(source)
    start=source.index("0xc9,4,0);c.branch(0xf0,'packed_header181')")
    end=source.index('checkimm(0x120e,0)',start)
    source=source[:start]+'''0xc9,4,0);c.branch(0x90,'ordinary547');c.emit(0xc9,9,0);c.branch(0x90,'packed_header181');c.label('ordinary547');'''+source[end:]
    return once(source,"def checkimm(a,v):lda(a);c.emit(0xc9);c.word(v);cond(0xd0,'bad_packet')",
                '''def checkimm(a,v):
  lda(a)
  if v:c.emit(0xc9);c.word(v)
  cond(0xd0,'bad_packet')''')


def direct(self,op,address):
    # Every caller runs in native mode at D=0, DBR=0. Use the equivalent
    # direct-page encoding for low unindexed scratch operands.
    # Fold only a symbolic JSR service immediately followed by LDA stop.
    pos=len(self.data)
    if (op,address)==(0xad,0x1236) and self.jumps and self.jumps[-1]==(pos-2,'service') and self.data[pos-3]==0x20 and self.base+pos not in self.labels.values():
        if getattr(self,'shared_exit547',False):
            self.folded547=getattr(self,'folded547',set())|{pos-2}
        else:
            self.jumps[-1]=(pos-2,'checked_service547')
        return
    short={0xed:0xe5,0x2d:0x25,0xae:0xa6,0xac:0xa4,0x8e:0x86,0x8c:0x84,0xec:0xe4,0xcc:0xc4}
    if address<256 and op in short:
        self.emit(short[op],address)
    else:
        original_absolute(self,op,address)


def group(source,early):
    source=original_group(source,early)
    a=source.index(" lda(0x125c);c.emit(0xc9,2,0)")
    b=source.index(" c.label('raw_charge489');",a)
    source=source[:a]+""" lda(0x125c);c.emit(0x0a,0x18);c.absolute(0x6d,0x1240);c.emit(0x3a,0x0a,0xaa)
 c.emit(0xbf,0,0,0x7e);c.jumps.append((len(c.data)-3,'charges547'))
"""+source[b:]
    return once(source," c.label('group538')", """ call(c,'prepare547');lda(0x1236);cond(0xd0,'cancel169')
 c.label('group538')""")


def raw_emitter(prepare=None):
    def edit(source):
        return once(source,"    lda(0x76);sta(0x2116);imm(64);",
                    """    c.emit(0x46,0x78);c.branch(0x90,'write547')
    lda(0x4302);c.emit(0x18,0x69,64,0);sta(0x4302);c.branch(0x80,'advance547')
    c.label('write547');lda(0x76);sta(0x2116);imm(64);""").replace(
            "    c.absolute(0xee,0x76);c.absolute(0xce,0x68);c.branch(0xd0,'raw_row489')",
            "    c.label('advance547');c.absolute(0xee,0x76);c.absolute(0xce,0x68);c.branch(0xd0,'raw_row489')")
    original=original_raw(edit)
    def emit(c):
        original(c)
        mark=c.label
        if not getattr(c,'shared_exit547',False):
            mark('checked_service547');call(c,'service');c.emit(0xad,0x36,0x12,0x60)
        mark('charges547')
        for size in (2656,3264,384,864,512,1120):c.word(size)
        if prepare is not None:
            prepare(c)
            return
        mark('prepare547')
        c.emit(0x64,0x78);c.absolute(0xad,0x1258);c.emit(0xc9,0x80,1);c.branch(0xd0,'exit547')
        # Save old eligibility in $125c (already decoded by compact489).
        # Clear the target bank tag before the first speculative shadow write.
        c.absolute(0xae,0x1034);c.emit(0xe2,0x20);c.absolute(0x9e,0x125a);c.emit(0xc2,0x20)
        c.absolute(0xad,0x1020);c.emit(0x18,0x69,0xdf,0x6a,0xaa)
        c.emit(0xe6,0x78)
        mark('row547');call(c,'service');c.absolute(0xad,0x1236);c.branch(0xd0,'exit547')
        c.emit(0xa0,32,0,0x38)
        mark('word547');c.long(0xbf,0x7f0000);c.long(0x5f,0x7e0000);c.branch(0xf0,'equal547')
        c.long(0xbf,0x7f0000);c.long(0x9f,0x7e0000);c.emit(0x18)
        mark('equal547');c.emit(0xca,0xca,0x88);c.branch(0xd0,'word547')
        c.emit(0x26,0x78,0xa5,0x78,0x89,64,0);c.branch(0xf0,'row547')
        c.absolute(0xad,0x125c);c.emit(0xc9,1,0);c.branch(0xf0,'exit547')
        c.emit(0x64,0x78)
        mark('exit547');c.emit(0x60)
    return emit


def build(out,shared_exit=False):
    def compact_packet(source):
        source=packet(source)
        if shared_exit:
            source=once(source,"c.label('service_done');c.emit(0x28,0x60)",
                        "c.label('service_done');c.emit(0x28,0xad,0x36,0x12,0x60)")
        return source
    with patch.object(nes_rawsteady181.RelaxCode,'shared_exit547',shared_exit,create=True), patch.object(nes_header546,'base_packet',compact_packet), patch.object(nes_rawsteady181.RelaxCode,'absolute',direct), \
         patch.object(nes_seal538,'group_upload',group), \
         patch.object(nes_seal538,'raw_service_inline',raw_emitter):
        r=nes_header546.build(out)
    if shared_exit:
        c=nes_rawsteady181.RelaxCode.latest
        callers={pos for pos,label in c.jumps if label=='service' and c.data[pos-1]==0x20}
        # The quiet loop ignores A/N/Z. Every other caller used LDA stop in
        # the restored accumulator width, now performed after PLP in service.
        assert callers-c.folded547=={c.labels['quiet']-c.base+1}
    r.update(candidate='history547',shared_exit=shared_exit,shadow_B=768,mask_DP=0x78)
    (out/'build.json').write_text(json.dumps(r,indent=2)+'\n')
    return r


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--shared-exit',action='store_true')
    args=parser.parse_args();print(build(args.out,args.shared_exit)['body_bytes'])
