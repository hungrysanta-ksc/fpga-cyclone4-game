# SPDX-License-Identifier: MIT
"""Full ARM candidate: packed1813 ingress and stream1815 egress.

The optional baseline retains the old converter stack for comparison only.
No deployable firmware/FPGA pair is produced by this preparation step.
"""
from pathlib import Path
import argparse,json
from nes_board181 import copy_pins
from nes_game147 import ROOT,sha
from nes_clip178 import replace
from nes_packed181 import receiver
from nes_stream181 import sink


def video(s):
    return replace(s,' uint8_t rank_used[224]={0},evaluation[224]={0};', ''' /* BG allocation and its final synchronous staging callback have finished.
  * No later lookup reads bg_keys. Borrow448 of its8192 bytes for OBJ checks;
  * the raw patch phase below clears its own complete region before reuse.
  * Byte access may alias the expired uint64_t keys, with no new allocation. */
 uint8_t *rank_used=(uint8_t *)p->bg_keys,*evaluation=rank_used+224;
 memset(rank_used,0,448);''')


def prepare(prior,out,baseline_stack=False):
    expected=json.loads((ROOT/'analysis/board181-verification.json').read_bytes())['verification']['arm']
    assert sha(prior/'src/obj-nes-100/firmware.stm')==expected['firmware_sha256']
    prep=json.loads((prior/'preparation-board181.json').read_bytes())
    pins=prep['copied']|prep['changed']|prep['added'];copy_pins(prior,out,pins)
    changed={}
    for src,dest,transform in [
        ('nes_native181.c','nes_native165.c',receiver),
        ('nes_native_sink181.c','nes_native_sink165.c',sink),
        ('nes_native_video181.c','nes_native_video165.c',str if baseline_stack else video)]:
        public=ROOT/'src/nes/firmware'/src
        # Exact prior production bodies, not an unrelated or stale baseline.
        assert public.read_bytes()==(prior/'src'/dest).read_bytes(),dest
        p=out/'src'/dest;p.write_text(transform(public.read_text()),encoding='utf8',newline='\n')
        if sha(p)!=pins['src/'+dest]:changed['src/'+dest]=sha(p)
    r=dict(copied=pins,changed=changed,added={},ingress_version='1813',sink_version='1815',
           expired_bg_workspace_reuse=not baseline_stack,hardware_package=False,
           public_sources={n:sha(ROOT/n) for n in ['tools/nes_paired181.py','tools/nes_packed181.py','tools/nes_stream181.py',
                'src/nes/firmware/nes_native181.c','src/nes/firmware/nes_native_sink181.c','src/nes/firmware/nes_native_video181.c']})
    for name in ('preparation-paired181.json','preparation-runlease165.json'):
        (out/name).write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('prior','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--baseline-stack',action='store_true');a=p.parse_args()
    r=prepare(a.prior,a.out,a.baseline_stack);print(json.dumps(dict(changed=r['changed'],hardware_package=False)))
