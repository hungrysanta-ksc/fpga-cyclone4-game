# SPDX-License-Identifier: MIT
"""Candidate1814 repeated-word DATA; no additional frame buffer or deployment.

op4: physical payload2, reserved header word = expanded even length4..240.
Sequential section bounds/ownership are checked before touching WRAM staging.
SEAL version1814; raw DATA and final display/STOP remain paired181 semantics.
"""
from pathlib import Path
import argparse, inspect, json
import nes_client181 as prior
from build_nes_trace_replay import Code
from nes_clip178 import replace

ROOT=Path(__file__).resolve().parents[1]

class ShortCode(Code):
    # All client routines run DP=0. Preserve width and flags; only addressing
    # encoding changes. No indexed/indirect instruction is rewritten.
    def absolute(self,op,address):
        short={0xad:0xa5,0x8d:0x85,0x6d:0x65,0xcd:0xc5,
               0x9c:0x64,0xee:0xe6,0xce:0xc6,0x0d:0x05}
        if address<256 and op in short:self.emit(short[op],address)
        else:super().absolute(op,address)

def source181(s):
    s=prior.source181(s)
    s=replace(s,'from build_nes_trace_replay import Code,Asm',
              'from build_nes_trace_replay import Asm\nfrom nes_sinkpack181 import ShortCode as Code')
    s=replace(s,'checkimm(0x120e,0);lda(0x120c);',
        "lda(0x1200);c.emit(0x29,255,0,0xc9,4,0);c.branch(0xf0,'packed_header181');checkimm(0x120e,0);c.label('packed_header181');lda(0x120c);")
    s=replace(s,"c.emit(0xc9,3,0);cond(0xf0,'seal');error()", """c.emit(0xc9,3,0);cond(0xf0,'seal')
 c.emit(0xc9,4,0);cond(0xd0,'bad_packet');checkimm(0x120c,2)
 lda(0x120e);c.emit(0xc9,4,0);cond(0x90,'bad_packet');c.emit(0xc9,241,0);cond(0xb0,'bad_packet')
 c.emit(0x89,1,0);cond(0xd0,'bad_packet');sta(0x120c);c.jump('data')""")
    s=replace(s,"c.emit(0xe2,0x20);c.store(0x2183,1)\n for a,v", """c.emit(0xe2,0x20);c.store(0x2183,1)
 lda(0x1200);c.emit(0xc9,4);c.branch(0xd0,'literal1814')
 c.absolute(0xac,0x120c);c.label('repeat1814')
 c.long(0xaf,0x400010);sta(0x2180);c.long(0xaf,0x400011);sta(0x2180)
 c.emit(0x88,0x88);c.branch(0xd0,'repeat1814');c.emit(0xc2,0x20);c.jump('accepted')
 c.label('literal1814')
 for a,v""")
    s=replace(s,'c.emit(0xc9,0x12,0x18)','c.emit(0xc9,0x14,0x18)')
    return s

def build(out):
    source=inspect.getsource(prior.build)
    namespace=dict(prior.__dict__);namespace['source181']=source181
    exec(compile(source,'sinkpack181-build','exec'),namespace)
    result=namespace['build'](out)
    result.update(scope=__doc__,sink_version='1814',seal_version='1814',additional_frame_ram=0)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result

def sink(s):
    s=replace(s,'put16(b+8,s->generation);put16(b+10,at);put16(b+12,n);if(n)memcpy(b+16,data,n);', '''put16(b+8,s->generation);put16(b+10,at);
 /* Only a whole identical-word packet is compressed; arbitrary bytes retain
  * DATA2. No hash, previous frame or retained callback pointer is used. */
 if(op==2 && data && n>=4 && !(n&1)){
  unsigned i=2;while(i<n && data[i]==data[i&1])i++;
  if(i==n){b[0]=4;put16(b+14,n);n=2;}
 }
 put16(b+12,n);if(n)memcpy(b+16,data,n);''')
    return replace(s,'put16(descriptor+20,0x1812)','put16(descriptor+20,0x1814)')

def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    (out/'nes_native_sink165.c').write_text(sink((ROOT/'src/nes/firmware/nes_native_sink181.c').read_text()),encoding='utf8',newline='\n')
    return build(out/'client')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    print(json.dumps(prepare(p.parse_args().out),indent=2))
