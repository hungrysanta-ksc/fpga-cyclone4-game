# SPDX-License-Identifier: MIT
"""Diagnostic contiguous bitmap masks; preserve receive/coverage ownership."""
from pathlib import Path
import argparse,inspect,json,shutil
import nes_sparse232 as prior
from nes_delta231 import once,sha


def transform(source,bits):
    a=source.index(" c.label('bits212');")
    b=source.index(' # Source and destination addresses',a)
    scale='c.emit(0x0a);' if bits==16 else ''
    narrow='c.emit(0xe2,0x20);' if bits==8 else ''
    wide='c.emit(0xc2,0x20);' if bits==8 else ''
    align='c.emit(0x29,0xfe,0xff);' if bits==16 else ''
    source=source[:a]+f''' maskfix=[]
 c.label('bits212');lda(0x6a);c.emit(0x29,{bits-1},0);sta(0x70)
 imm({bits});c.emit(0x38);c.absolute(0xed,0x70);c.absolute(0xcd,0x6c);c.branch(0x90,'range_take247');lda(0x6c)
 c.label('range_take247');sta(0x72)
 lda(0x70);{scale}c.emit(0xaa);maskfix.append(len(c.data)+1);c.long(0xbf,0);c.emit(0x49,255,255);sta(0x74)
 lda(0x70);c.emit(0x18);c.absolute(0x6d,0x72);{scale}c.emit(0xaa);maskfix.append(len(c.data)+1);c.long(0xbf,0);c.absolute(0x2d,0x74);sta(0x74)
 lda(0x6a);c.emit(0x4a,0x4a,0x4a);{align}c.emit(0xaa,0x18);c.absolute(0x6d,0x1254);c.emit(0xa8)
 {narrow}c.absolute(0xbd,0x1280);c.absolute(0x2d,0x74);{wide}cond(0xd0,'mark_bad212')
 {narrow}c.absolute(0xbd,0x1280);c.absolute(0x0d,0x74);c.absolute(0x9d,0x1280)
 c.absolute(0xb9,0x1380);c.absolute(0x0d,0x74);c.absolute(0x99,0x1380);{wide}
 lda(0x6a);c.emit(0x18);c.absolute(0x6d,0x72);sta(0x6a)
 lda(0x6c);c.emit(0x38);c.absolute(0xed,0x72);sta(0x6c);cond(0xd0,'bits212')
'''+source[b:]
    table=f''' c.label('range_masks247')
 for fix in maskfix:c.data[fix:fix+3]=(c.base+len(c.data)).to_bytes(3,'little')
 for i in range({bits+1}):
  value=(1<<i)-1
  {'c.word(value)' if bits==16 else 'c.emit(value)'}
 {'c.emit(0)' if bits==8 else '# Complete word table, including prefix16.'}
'''
    return once(source,' return dict(',table+' return dict(')


def install(bits):
    source=inspect.getsource(prior.emit)
    source=once(source,"lda(0x60);c.emit(0xc9,4,0);cond(0x90,'append_new212');lda(0x7c);","lda(0x7c);")
    source=once(source,' ns=dict(old.__dict__);exec(',f' s=transform(s,{bits})\n ns=dict(old.__dict__);exec(')
    ns=dict(prior.__dict__);ns['transform']=transform
    exec(compile(source,'rangemark247-snes','exec'),ns);prior.emit=ns['emit']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--word-bits',type=int,choices=(8,16),default=16)
    a=p.parse_args();install(a.word_bits);r=prior.build(a.out.resolve())
    r.update(candidate='rangemark247_diagnostic',mask_bits=a.word_bits,post_seal_scan=False,
             script_sha256=sha(Path(__file__)),extra_persistent_bytes=0,charge_policy=4192,
             implementation_selected=False,runtime_verified=False)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(__file__,a.out/'builder.py')
    print(json.dumps({k:r[k] for k in ('body_bytes','body_free','program_bytes','mask_bits')},indent=2))


if __name__=='__main__':main()
