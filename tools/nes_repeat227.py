# SPDX-License-Identifier: MIT
"""227: exact repeated4-byte OAM tail, no cache or skipped display data."""
from pathlib import Path
import argparse, inspect, json
from nes_fast226 import ROOT, BASE, sha, once
from nes_board181 import copy_pins
import nes_dirty212 as client


def sink(s):
    s=s.replace('0x2121','0x2271')
    s=once(s,' if(op!=5&&op!=6&&op!=7&&expanded)', ''' if(op==8&&(!data||section!=4||n!=4||expanded<8||expanded>512||
    (at&3)||(expanded&3)||at+expanded>512))return fail(s,1);
 if(op!=5&&op!=6&&op!=7&&op!=8&&expanded)''')
    s=once(s,'b[0]==5||b[0]==6)', 'b[0]==5||b[0]==6||b[0]==8)')
    # Reuse exact legacy estimator and sender; no persistent state.
    pos=s.index('\nbool nes_sink165_begin')
    s=s[:pos]+'''
static unsigned span_cost227(const uint8_t *b,unsigned n){
 unsigned old=0,split=0;
 for(unsigned at=0;at<n;){unsigned count=n-at;if(count>240)count=240;
  old+=data_cost(b+at,count);at+=count;}
 for(unsigned at=0;at<n;){unsigned count=span_piece(b+at,n-at);
  split+=data_cost(b+at,count);at+=count;}
 return old<split?old:split;
}
static bool oam227(struct nes_native_sink165 *s,const uint8_t *b){
 /* Last32B are packed high attributes, never part of the repeated4B tail.
  * Compare every byte; valid objects and hidden objects are treated alike. */
 unsigned first=508;
 while(first>=4&&!memcmp(b+first-4,b+508,4))first-=4;
 unsigned length=512-first;
 unsigned cost=(first?span_cost227(b,first):0)+471+8*4+span_cost227(b+512,32);
 if(length<64||repeat_bytes(b+first,length)==length||cost>=span_cost227(b,544))
  return span(s,4,0,b,544);
 if(first&&!span(s,4,0,b,first))return false;
 return packet_wire(s,8,4,first,b+first,4,length)&&span(s,4,512,b+512,32);
}
''' + s[pos:]
    return once(s,' for(unsigned k=3;k<6;k++)if(!span(s,k,0,data[k-2],size[k]))return false;',
        ' for(unsigned k=3;k<6;k++)if(!(k==4?oam227(s,data[k-2]):span(s,k,0,data[k-2],size[k])))return false;')


def source(s):
    s=client.source181(s)
    s=s.replace('0x21,0x21','0x71,0x22')
    s=once(s,"c.emit(0xc9,7,0);c.branch(0xf0,'packed_header181');",
        "c.emit(0xc9,7,0);c.branch(0xf0,'packed_header181');c.emit(0xc9,8,0);c.branch(0xf0,'packed_header181');")
    s=once(s," c.emit(0xc9,7,0);cond(0xf0,'bulk194')", """
 c.emit(0xc9,8,0);cond(0xf0,'repeat227')
 c.emit(0xc9,7,0);cond(0xf0,'bulk194')""")
    s=once(s," c.label('bulk194');", """
 c.label('repeat227');checkimm(0x120c,4)
 lda(0x1201);c.emit(0x29,255,0,0xc9,4,0);cond(0xd0,'bad_packet')
 lda(0x120e);c.emit(0xc9,8,0);cond(0x90,'bad_packet');c.emit(0xc9,1,2);cond(0xb0,'bad_packet')
 sta(0x70);c.absolute(0x0d,0x120a);c.emit(0x29,3,0);cond(0xd0,'bad_packet')
 lda(0x70);c.emit(0x18);c.absolute(0x6d,0x120a);cond(0xb0,'bad_packet');c.emit(0xc9,1,2);cond(0xb0,'bad_packet')
 lda(0x70);sta(0x120c);c.jump('data')
 c.label('bulk194');""")
    s=once(s,'sta(0x2181)', 'sta(0x2181);sta(0x7a)')
    s=once(s,"c.emit(0xc2,0x20);lda(0x120c);sta(0x4305);",
        """c.emit(0xc2,0x20);lda(0x120c);sta(0x4305)
 lda(0x1200);c.emit(0x29,255,0,0xc9,8,0);c.branch(0xd0,'literal_length227');imm(4);sta(0x4305)
 c.label('literal_length227');""")
    s=once(s,"c.store(0x420b,1);c.emit(0xc2,0x20);c.jump('accepted')",
        """c.store(0x420b,1);c.emit(0xc2,0x20)
 lda(0x1200);c.emit(0x29,255,0,0xc9,8,0);c.branch(0xd0,'repeat_done227')
 # First4B are now in candidate WRAM. Forward overlapping MVN repeats them.
 # MVN changes DB; preserve it before any further absolute metadata access.
 c.emit(0x8b);c.absolute(0xae,0x7a);lda(0x7a);c.emit(0x18,0x69,4,0,0xa8)
 lda(0x120c);c.emit(0x38,0xe9,5,0,0x54,0x7f,0x7f,0xab)
 call(c,'service');lda(0x1236);cond(0xd0,'stop_packet')
 c.label('repeat_done227');c.jump('accepted')""")
    return s


def build(out):
    s=inspect.getsource(client.build)
    ns=dict(client.__dict__);ns.update(source181=source)
    exec(compile(s,'repeat227-build','exec'),ns)
    # Avoid recursion: compiled function is old body, whose source181 is new.
    result=ns['build'](out)
    result.update(candidate='repeat227',sink_version='2271',seal_version='2271',
                  repeat_period=4,repeat_max=512,extra_persistent_ram=522,new_frame_ram=False,scope=__doc__)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


def prepare(out):
    prior=BASE/'probes/nes-fast226/arm01'
    p=json.loads((prior/'preparation-fast226.json').read_bytes())
    pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins)
    f=out/'src/nes_native_sink165.c';f.write_text(sink(f.read_text()),encoding='utf8',newline='\n')
    f=out/'src/nes_sink_window184.c';f.write_text(once(f.read_text(),
        'p[0]!=5&&p[0]!=6)', 'p[0]!=5&&p[0]!=6&&p[0]!=8)'),encoding='utf8',newline='\n')
    for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
        f=out/'src'/n;f.write_text(f.read_text().replace('226','227'),encoding='utf8',newline='\n')
    changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h}
    result=dict(copied=pins,changed=changed,added={},public_sources={'tools/nes_repeat227.py':sha(Path(__file__))},
                new_fpga_logic=False,new_snes_rom=True,new_data_state_bytes=0,physical=False)
    (out/'preparation-repeat227.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--client',action='store_true')
    a=p.parse_args();result=build(a.out) if a.client else prepare(a.out)
    print(json.dumps(result if a.client else result['changed']))
