"""Build independent ARM scheduling candidates from the released MMC855 source."""
import argparse
from pathlib import Path

from nes_raw506 import once
from prepare_nes_trial802 import PROBES


def shared_completion(code):
    # FINISH is called only from progress(). It can retire fresh and repeated
    # descriptors at the same point after checking the complete identity.
    code = once(code, "    if(phase==NES_PLAN215_FINISH&&!complete485(p))return false;\n", "")
    code = once(code, "(uint16_t)(p->window->sent-p->window->retired)<=2",
                "(uint16_t)(p->window->sent-p->bulk_until)<3")
    begin = code.index("   /* A repeat was already checked")
    end = code.index("   if((mode==NES_MAP553", begin)
    return code[:begin] + """   /* Both new and repeated descriptors retain their checked identity.
    * Keep the receipt within the four-head window; enqueue checks credit. */
""" + code[end:]


def early_ordinary(code):
    anchor = " uint8_t flags;\n for(unsigned i=0;i<p->poll_limit;i++){\n  if(!poll(p,&flags,NES_PLAN215_FINISH))"
    return once(code, anchor, """ /* The current OBJ already owns a checked descriptor. Its receipt stays
  * reachable while at most three more queue heads are issued. Section 5
  * is immutable here; send() still checks STOP and real queue credit. */
 if(mode==NES_ORDINARY553 && p->bulk_pending && p->bulk[1] &&
    p->window->last[1]==5 && (uint16_t)(p->window->sent-p->bulk_until)<3)
  return valid(p);
""" + anchor)


def split_tail(code):
    start = code.index("  if(!packet(s,2,5,offset,tables,240))")
    end = code.index("  size[5]", start)
    # Keep the 243 table bytes and six length bytes contiguous on the wire.
    # The alignment padding in the enclosing ARM struct is not a wire byte.
    return code[:start] + """  if(!packet(s,2,5,offset,tables,128))return false;
  uint8_t tail[121];
  memcpy(tail,tables+128,115);
  memcpy(tail+115,p->patch.size,6);
  if(!packet(s,2,5,offset+128,tail,sizeof tail))return false;
""" + code[end:]


def immediate_receipt(code):
    code = once(code, "    if(phase==NES_PLAN215_FINISH&&!complete485(p))return false;",
                """    if(phase==NES_PLAN215_FINISH && p->bulk_pending){
     if(!complete485(p))return false;
     /* Real retirement warrants one immediate checked producer query. */
     result|=8;
    }""")
    anchor = "  if(flags&2){p->finished=true;return true;}"
    return once(code, anchor, anchor+"\n  if(flags&8)continue;")


def raw_successor(code):
    anchor = " if(p->finished)return valid(p);"
    # Read both header bytes without assuming alignment or type punning.
    return once(code, anchor, """ /* Defer exactly the query after a checked section-5 word fill. The
  * following ordinary head cannot displace the outstanding receipt. */
 if(p->finished || (mode==NES_ORDINARY553 && p->bulk_pending &&
    !memcmp(p->window->last,"\\004\\005",2) &&
    (uint16_t)(p->window->sent-p->bulk_until)<3))return valid(p);""")


def shared_fault(code):
    # Keep the first-fault latch in one place, including on builds where -Os
    # duplicates it at each cold exit. Healthy packet processing never calls it.
    return once(raw_successor(code), "static bool fail(struct nes_plan200",
                "static __attribute__((noinline)) bool fail(struct nes_plan200")


POLICIES = {'a': early_ordinary, 'b': shared_completion, 'c': split_tail,
            'd': immediate_receipt, 'e': raw_successor, 'f': shared_fault, 'g': shared_fault,
            'h': shared_fault}


def prepare(out, variant):
    filename = 'nes_native_sink165.c' if variant == 'c' else 'nes_plan_service200.c'
    source = PROBES / 'nes-trial855/link/src' / filename
    code = POLICIES[variant](source.read_text())
    if variant == 'h':
        # The token decoder compiles to a single little-endian load on M4.
        code = once(code, 'static uint32_t token485(',
                    'static inline __attribute__((always_inline)) uint32_t token485(')
    out.mkdir(parents=True)
    (out / filename).write_text(code)
    if variant in ('g','h'):
        sink = source.with_name('nes_native_sink165.c')
        code = once(sink.read_text(), 'static bool fail(struct nes_native_sink165',
                    'static __attribute__((cold,noinline)) bool fail(struct nes_native_sink165')
        (out / sink.name).write_text(code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('variant', choices=POLICIES)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    prepare(args.out, args.variant)
