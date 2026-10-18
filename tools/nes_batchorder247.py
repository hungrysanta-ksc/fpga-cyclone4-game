# SPDX-License-Identifier: MIT
"""Diagnostic batch insertion helper and receive-time pattern-gap consumer."""
from pathlib import Path
import argparse,inspect,json,shutil
import nes_sparse232 as prior
from nes_delta231 import once,sha

HEADER=r'''/* SPDX-License-Identifier: MIT */
/* Internal validated196/199 encoded plans only. Insert before framing/CRC.
 * Existing append owns encoded[32]; no extra frame buffer or retained state. */
static unsigned order247_length(const uint8_t *b){
 if(b[0]&128)return b[0]==128?7:b[0]==129?8:3;
 unsigned n=16;for(unsigned m=b[1];m;m>>=1)n+=(m&1)*2;return n;
}
static unsigned order247_key(const uint8_t *b){
 unsigned kind=b[0]&3;if(kind>=2)return kind==2?0:65535;
 unsigned at=(b[0]&128)?3:4;return kind*1024+b[at]+256u*b[at+1];
}
static void order247_insert(uint8_t *buffer,unsigned size,const uint8_t *encoded,unsigned n){
 unsigned at=0,key=order247_key(encoded);
 while(at<size&&order247_key(buffer+at)<=key)at+=order247_length(buffer+at);
 memmove(buffer+at+n,buffer+at,size-at);memcpy(buffer+at,encoded,n);
}
'''


def install():
    source=inspect.getsource(prior.emit)
    source=once(source,"lda(0x60);c.emit(0xc9,4,0);cond(0x90,'append_new212');lda(0x7c);", "lda(0x7c);")
    ns=dict(prior.__dict__);exec(compile(source,'batchorder247-snes','exec'),ns);prior.emit=ns['emit']


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();install();r=prior.build(a.out.resolve())
    r.update(candidate='batchorder247_diagnostic',scope=__doc__,script_sha256=sha(Path(__file__)),
             pattern_gap_allowed_after_coverage=True,post_seal_scan=False,extra_persistent_bytes=0,charge_policy=4192,
             implementation_selected=False,runtime_verified=False)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    (a.out/'order247.h').write_text(HEADER,encoding='utf-8',newline='\n');shutil.copyfile(__file__,a.out/'builder.py')
    print(json.dumps({k:r[k] for k in ('body_bytes','body_free','program_bytes','post_seal_scan')},indent=2))


if __name__=='__main__':main()
