# SPDX-License-Identifier: MIT
"""Borrow a checked post-FINISH queue-credit opportunity for one input block."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha
from prepare_nes_capture785 import shrink_headers

BASE_ELF = "62265e2b240feecd9562216577617ea30e3a93abfe9f71b90887bf19339da6aa"

def prepare(base, out, mode, compact=False, sticky=False):
    assert sha(base / "obj-nes-100/sd2snes.elf") == BASE_ELF
    name = "nes_native_runtime165.c"
    code = (base / name).read_text()
    # Reason 0 follows the credit check; reason 1 can be the completion of
    # a map run. Never interpose on a successful map drain, or before FINISH.
    policies = {
        "credit": "(!progress || reason==0)",
        "first": "(!progress || (reason==0 && s->prefetch_left==7))",
        # A single-page upload with completed geometry can service its next
        # input at ordinary credit, without breaking a two-page map chain.
        "page": "(!progress || (reason==0 && s->resident && !(uint32_t)s->resident->map_upload))",
        "head": "(!progress || (reason==0 && s->transport.last[1]>=3))",
    }
    out.mkdir(parents=True, exist_ok=False)
    policy = "credit" if mode == "map_gap" else mode
    if policy in policies:
        code = once(code, "reason<=1 && s->plan.finished && !progress;",
                    "reason<=1 && s->plan.finished && "+policies[policy]+";")
    else:
        # FINISH has checked the empty descriptor and drained its receipt.
        # The runtime wait also checks prepared geometry before releasing it.
        name = "nes_plan_service200.c"
        code = (base / name).read_text()
        if mode in ("service","service_burst","release"):
            finish = "return wait485(p);"
            if mode in ("service_burst","release"):
                # Existing waits before FINISH retain their original reason.
                code = once(code, "p->window->ctx,p->window->guard,0,false)",
                            "p->window->ctx,p->window->guard,p->finished?3:0,false)")
        else:
            reason = 3 if mode == "drain" else 4
            finish = (f"return !p->window || !p->window->wait || "
                      f"p->window->wait(p->ctx,p->guard,{reason},false) || fail(p,2);")
        code = once(code, "if(flags&2){p->finished=true;return true;}",
                    "if(flags&2){p->finished=true;"+finish+"}")
    (out / name).write_text(code, newline="\n")

    if mode == "release":
        # On a final right-only run, honor a ready tile between map heads.
        # Keep the actual packet (op2), CRC, credit and destinations unchanged.
        name = "nes_native_sink165.c"
        code = (base / name).read_text()
        code = once(code, "if(op==24)op=2;", "if(op==24 || op==25)op=2;")
        code = once(code, "(early==1||adjacent)?24:2,2,first*64",
                    "(early==1||adjacent)?24:!early && !(uint32_t)mask?25:2,2,first*64")
        (out / name).write_text(code, newline="\n")

    if mode == "map_gap":
        # A returned map head followed by a ready OBJ can close an older
        # contiguous VRAM run. Observe real progress while the queue is
        # drained; bound the sample count when the beam is outside VBlank.
        name = "nes_plan_service200.c"
        code = (base / name).read_text()
        old = """if(!nes_window184_drain(p->window,ack) ||
       (!(p->window->status_flags&8) &&
        !p->window->wait(p->window->ctx,p->window->guard,4,false)))return fail(p,5);"""
        code = once(code, old, """unsigned attempts = d[1] && p->window->last[1]==2 && !p->sink->obj_next ? 4 : 1;
    do {
     if(!nes_window184_drain(p->window,ack))return fail(p,5);
     if(p->window->status_flags&8)break;
     if(!p->window->wait(p->window->ctx,p->window->guard,4,false))return fail(p,5);
    } while(--attempts);""")
        (out / name).write_text(code,newline="\n")

    if compact:
        name = "nes_menu_diagnostic.c"
        (out / name).write_bytes((base / name).read_bytes())
        shrink_headers(out)
        if mode in ("page","release","map_gap"):
            # The shared report append already propagates a negative offset.
            name = "nes_menu_diagnostic.c"
            text = (out / name).read_text()
            text = once(text, 'int used=snprintf(text+n,size-(size_t)n,"ppu_history_%02u=",i);\n  if(used<0||(size_t)used>=size-(size_t)n)return -1;\n  n=nes_hexline512(text,size,n+used,h,12);',
                        'n=nes_report_packed782(text,size,n,"ppu_history_%02u=",i);\n  n=nes_hexline512(text,size,n,h,12);')
            (out / name).write_text(text, newline="\n")

    if sticky:
        # As in 785V, the append helper propagates truncation.
        name = "nes_budget210.c"
        text = (base / name).read_text()
        start = text.index("int nes_budget210_format")
        end = text.index(" for(unsigned i=0;i<12;i++)",start)
        text = text[:start]+text[start:end].replace("if(n<0)return -1;", "")+text[end:]
        (out / name).write_text(text,newline="\n")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("base", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("mode", choices=("credit","first","head","page","finish","drain","service","service_burst","release","map_gap"))
    p.add_argument("--compact", action="store_true")
    p.add_argument("--sticky", action="store_true")
    args = p.parse_args()
    prepare(args.base, args.out, args.mode, args.compact, args.sticky)
