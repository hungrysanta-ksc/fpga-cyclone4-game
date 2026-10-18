# SPDX-License-Identifier: MIT
"""P1 diagnostic code-size probe: replace receive-time list construction.

Not a selected product candidate. Keep232 coverage/4192/uploader/ACK intact.
"""
from pathlib import Path
import argparse,inspect,json,shutil
import nes_sparse232 as prior
from nes_delta231 import once,sha


def transform(s):
    start=s.index(' # Source and destination addresses')
    end=s.index(" c.label('mark_bad212');",start)
    s=s[:start]+" c.emit(0x38,0x60)\n"+s[end:]
    start=s.index(' # List entries source/dest/size')
    end=s.index(' # Used slots must be initialized',start)
    s=s[:start]+s[end:]
    start=s.index(' for values,fix in ')
    end=s.index(' return dict(',start)
    s=s[:start]+s[end:]
    return s


def scanner(c):
    start=len(c.data)
    def lda(a):c.absolute(0xad,a)
    def sta(a):c.absolute(0x8d,a)
    def imm(a):c.emit(0xa9);c.word(a)
    def cond(op,label):c.emit(op^0x20,3);c.jump(label)
    def call(label):prior.call(c,label)
    fixes=[]
    def table(column):
        pos=len(c.data);c.long(0xbf,0);fixes.append((pos+1,column))
    c.label('scan247');c.absolute(0x9c,0x1250);c.absolute(0x9c,0x60)
    c.label('scan_group247');c.absolute(0xae,0x60)
    for column,at in ((0,0x62),(2,0x64),(4,0x66)):
        table(column);sta(at)
    table(6);c.emit(0x18);c.absolute(0x6d,0x1020);sta(0x70)
    lda(0x1034);c.emit(0x0a,0x18);c.absolute(0x6d,0x60);c.emit(0xaa);table(8);sta(0x72)
    imm(1);sta(0x68);c.absolute(0x9c,0x74);c.absolute(0x9c,0x76)
    c.label('scan_service247');call('service');lda(0x1236);cond(0xd0,'scan_bad247')
    c.label('scan_bit247');c.emit(0xb2,0x62);c.absolute(0x2d,0x68);cond(0xf0,'scan_zero247')
    lda(0x74);cond(0xf0,'scan_new247');lda(0x76);c.emit(0xc9,97,0);cond(0xb0,'scan_flush247')
    c.emit(0x18);c.absolute(0x6d,0x74);c.absolute(0x6d,0x66);c.emit(0xc9,1,16);cond(0x90,'scan_length247')
    c.label('scan_flush247');call('scan_emit247');cond(0x90,'scan_bad247')
    c.label('scan_new247');lda(0x66)
    c.label('scan_length247');sta(0x74);c.absolute(0x9c,0x76);c.jump('scan_next247')
    c.label('scan_zero247');lda(0x76);c.emit(0x18);c.absolute(0x6d,0x66);sta(0x76)
    c.label('scan_next247')
    for at in (0x70,0x72):lda(at);c.emit(0x18);c.absolute(0x6d,0x66);sta(at)
    c.absolute(0xce,0x64);cond(0xf0,'scan_end247')
    lda(0x68);c.emit(0x0a);sta(0x68);c.emit(0xc9,0,1);cond(0x90,'scan_bit247')
    imm(1);sta(0x68);c.absolute(0xee,0x62);c.jump('scan_service247')
    c.label('scan_end247');call('scan_emit247');cond(0x90,'scan_bad247')
    lda(0x60);c.emit(0x18,0x69,12,0);sta(0x60);c.emit(0xc9,48,0);cond(0x90,'scan_group247')
    c.label('scan_ok247');c.emit(0x38,0x60)
    c.label('scan_bad247');c.emit(0x18,0x60)
    c.label('scan_emit247');lda(0x74);cond(0xf0,'scan_ok247')
    lda(0x1250);c.emit(0xc9,0,48);cond(0xb0,'scan_bad247');c.emit(0xaa)
    for at,dest in ((0x70,0x7e4000),(0x72,0x7e4002)):
        lda(at);c.emit(0x38);c.absolute(0xed,0x76);c.emit(0x38);c.absolute(0xed,0x74);c.long(0x9f,dest)
    lda(0x74);c.long(0x9f,0x7e4004);imm(0);c.long(0x9f,0x7e4006)
    c.emit(0x8a,0x18,0x69,8,0);sta(0x1250);c.emit(0x38,0x60)
    c.label('scan_table247');table_at=c.base+len(c.data)
    # bitmap pointer,unit count,unit bytes,WRAM offset,VRAM A,VRAM B.
    for row in ((0x1280,1024,16,0,0,0xc000),
                (0x1300,128,32,0x4000,0x4000,0x8000),
                (0x1310,256,16,0x5000,0x6000,0xa000),
                (0x1334,128,16,0x6961,0x5000,0x9000)):
        for value in row:c.word(value)
    for pos,column in fixes:c.data[pos:pos+3]=(table_at+column).to_bytes(3,'little')
    return len(c.data)-start


def install():
    source=inspect.getsource(prior.emit)
    source=once(source,' ns=dict(old.__dict__);',' s=transform(s)\n ns=dict(old.__dict__);')
    source=once(source,"return ns['emit'](c,prefix,service)","result=ns['emit'](c,prefix,service);result['scanner_bytes']=scanner(c);return result")
    ns=dict(prior.__dict__);ns.update(transform=transform,scanner=scanner)
    exec(compile(source,'scan247-emit','exec'),ns)
    original_source=prior.source
    def new_source(s):
        s=original_source(s)
        return once(s,"call(c,'coverage212');cond(0x90,'bad_packet')", "call(c,'coverage212');cond(0x90,'bad_packet');call(c,'scan247');cond(0x90,'bad_packet')")
    prior.emit=ns['emit'];prior.source=new_source


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();install();result=prior.build(a.out.resolve())
    result.update(scope=__doc__,candidate='scan247_diagnostic',script_sha256=sha(Path(__file__)),
                  implementation_selected=False,coverage_unchanged=True,charge_policy=4192,
                  scan_slots=1536,service_every_slots=8,extra_persistent_state_bytes=0,
                  runtime_verified=False,physical=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(Path(__file__),a.out/'builder.py')
    print(json.dumps({k:result[k] for k in ('body_bytes','body_free','program_bytes','local','runtime_verified')},indent=2))


if __name__=='__main__':main()
