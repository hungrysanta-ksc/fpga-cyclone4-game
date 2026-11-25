"""Try issuing immutable ordinary heads before the remaining 23-row map drain."""
import argparse
import json
import shutil
from pathlib import Path

from nes_tail1013 import BASE, ROOT, once
from nes_raw506 import sha

WORK = BASE.with_name("nes-overlap1018")


def prepare(mode):
    original = BASE / "link"
    ref = json.loads((ROOT / "analysis/trial1012-package.json").read_bytes())
    assert sha(original / "src/obj-nes-100/firmware.stm") == ref["firmware"]
    dst = WORK / mode / "link"
    shutil.copytree(original, dst, ignore=shutil.ignore_patterns("*.log"))
    source = dst / "src/nes_native_sink165.c"
    code = source.read_text()
    old = " if(!map527(s,p,r->map_upload,false))return false;"
    code = once(code, old, """ bool early_tail = r->map_upload==0x7fffff && p->patch_count==1 &&
                   p->scroll_issued && s->displayed && s->ack635[r->target] &&
                   s->ack635[1-r->target] && same635(s,p);
 if(!early_tail && !map527(s,p,r->map_upload,false))return false;""")
    if mode=="maphead":
        code=once(code," if(!early_tail && !map527(s,p,r->map_upload,false))return false;",
                  " if(!map527(s,p,r->map_upload,early_tail?1:0))return false;")
    point = ("  if(!packet(s,2,5,offset+201,joined+201,240))return false;" if mode=="prefix" else
             " /* Old identity no longer owns the buffer. Publish only after final ACK. */")
    code = once(code, point, " if(early_tail && !map527(s,p,r->map_upload,false))return false;\n" + point)
    if mode=="credit":
        # Lend at most two ordinary heads to the confirmed bulk owner. The
        # queue's four-head history still contains its receipt when polled.
        for offset in ("offset","offset+201"):
            old_head=f"packet(s,2,5,{offset},"
            new_head=("packet(s,(early_tail && s->plan->bulk_pending && s->plan->bulk[1] && "
                      "(uint16_t)(s->plan->window->sent-s->plan->bulk_until)<2)?24:2,5,"
                      f"{offset},")
            code=once(code, old_head+"joined", new_head+"joined")
    # The eligibility check already validated the unchanged palette/OAM tail.
    code = once(code, " bool same=same635(s,p);", " bool same=early_tail || same635(s,p);")
    source.write_text(code, newline="\n")


def replay(temp,phase,mode):
    from replay_nes_tail1013 import run
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0
    marks=[]
    def instrument(cpu):
        def mark(name):
            def sample(u,*_):
                row=dict(g=cpu.generation,clock=cpu.clock,event=name)
                if name=="ready1012":
                    head=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R0),16))
                    row.update(g=int.from_bytes(head[8:10],"little"),op=head[0],section=head[1],
                               offset=int.from_bytes(head[10:12],"little"))
                marks.append(row)
            return sample
        for name in ("nes_sink212_seal","ready1012"):
            pc=cpu.syms[name]
            cpu.u.hook_add(UC_HOOK_CODE,mark(name),begin=pc,end=pc)
    def client(lua):
        return once(lua,'step920("consume920");consumed[','sample516("return1018",pw(16)+65536*pw(18));step920("consume920");consumed[')
    tag="1018wire-"+mode
    firmware=(BASE if mode=="control" else WORK/mode)/"link/src"
    run(temp,phase,"control",firmware=firmware,tag=tag,observe_arm=instrument,observe_client=client)
    (temp/f"nes-tile821-late-jointmirror-p{phase}-{tag}/arm1018.json").write_text(json.dumps(marks))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("control","prefix","group","credit","maphead"))
    parser.add_argument("--phase",type=int,choices=(1,2))
    parser.add_argument("--temp",type=Path)
    args=parser.parse_args()
    if args.phase and args.temp is None:
        parser.error("--phase requires --temp")
    if args.mode=="control" and not args.phase:
        parser.error("control uses the existing MMC1012 link; specify --phase and --temp")
    if args.phase:
        replay(args.temp,args.phase,args.mode)
    else:
        prepare(args.mode)
